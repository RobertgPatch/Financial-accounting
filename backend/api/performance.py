"""
Performance calculation engine for TWR, IRR/XIRR, and period utilities.

Pure Python implementation per research.md — no numpy-financial dependency.
Uses Newton's method for XIRR, geometric linking for TWR.
"""
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from .models import Asset, FMVSnapshot, Distribution, EntityAssetOwnership


# ---------------------------------------------------------------------------
# Period date resolver (T042)
# ---------------------------------------------------------------------------

def resolve_period(period_key, calc_date=None):
    """
    Resolve a period key to a (start_date, end_date, label) tuple.

    Supported keys: ytd, 1y, 3y, 5y, since_inception, custom.
    For 'since_inception', start_date is returned as None (caller determines from data).
    """
    calc_date = calc_date or date.today()
    periods = {
        'ytd': (date(calc_date.year, 1, 1), calc_date, 'YTD'),
        '1y': (calc_date - timedelta(days=365), calc_date, '1 Year'),
        '3y': (calc_date - timedelta(days=1095), calc_date, '3 Year'),
        '5y': (calc_date - timedelta(days=1826), calc_date, '5 Year'),
        'since_inception': (None, calc_date, 'Since Inception'),
    }
    return periods.get(period_key, periods['since_inception'])


def should_annualize(start_date, end_date):
    """Returns True if the period spans more than 1 year."""
    return (end_date - start_date).days > 365


def annualize_return(total_return, days):
    """Annualize a total return given the number of days.

    Args:
        total_return: Cumulative return as a decimal (e.g., 0.15 for 15%).
        days: Number of calendar days in the period.
    """
    if days <= 0 or total_return <= -1:
        return total_return
    return (1 + total_return) ** (365.25 / days) - 1


# ---------------------------------------------------------------------------
# TWR — Time-Weighted Return (T040)
# ---------------------------------------------------------------------------

def calculate_twr(asset_id, start_date, end_date):
    """
    Calculate the True Time-Weighted Return for an asset using
    sub-period geometric linking.

    Returns dict with 'twr', 'annualized_twr', 'sub_periods', 'data_quality'.
    Returns None-valued result if insufficient data.
    """
    snapshots = list(
        FMVSnapshot.objects.filter(
            asset_id=asset_id,
            snapshot_date__gte=start_date,
            snapshot_date__lte=end_date,
        ).order_by('snapshot_date').values('snapshot_date', 'value')
    )

    if len(snapshots) < 2:
        return _insufficient_twr('Need at least 2 FMV snapshots in the period')

    # Collect distributions in the period
    distributions = list(
        Distribution.objects.filter(
            asset_id=asset_id,
            distribution_date__gte=start_date,
            distribution_date__lte=end_date,
        ).order_by('distribution_date').values('distribution_date', 'total_amount')
    )

    # Build date → total distribution map
    dist_by_date = defaultdict(float)
    for d in distributions:
        dist_by_date[d['distribution_date']] += float(d['total_amount'])

    # Calculate sub-period growth factors
    growth_factors = []
    sub_periods = []
    for i in range(1, len(snapshots)):
        v_start = float(snapshots[i - 1]['value'])
        v_end = float(snapshots[i]['value'])
        d_start = snapshots[i - 1]['snapshot_date']
        d_end = snapshots[i]['snapshot_date']

        # Sum distributions between start (exclusive) and end (inclusive)
        # Distributions flow OUT of the asset → negative for TWR
        cf_out = 0.0
        for dd, amt in dist_by_date.items():
            if d_start < dd <= d_end:
                cf_out += amt

        denominator = v_start - cf_out  # subtract distributions (money left in asset)
        if denominator <= 0:
            # Skip sub-period where start value after outflows is zero/negative
            continue

        gf = v_end / denominator
        growth_factors.append(gf)
        sub_periods.append({
            'start_date': str(d_start),
            'end_date': str(d_end),
            'start_value': v_start,
            'end_value': v_end,
            'cash_flows': -cf_out,
            'growth_factor': round(gf, 6),
        })

    if not growth_factors:
        return _insufficient_twr('No valid sub-periods could be calculated')

    # Geometric linking
    twr = 1.0
    for gf in growth_factors:
        twr *= gf
    twr -= 1.0

    total_days = (end_date - start_date).days
    annualized = annualize_return(twr, total_days) if should_annualize(start_date, end_date) else None

    # Data quality
    staleness_days = (end_date - snapshots[-1]['snapshot_date']).days

    return {
        'twr': round(twr * 100, 4),  # percentage
        'annualized_twr': round(annualized * 100, 4) if annualized is not None else None,
        'sub_periods': sub_periods,
        'data_quality': {
            'snapshot_count': len(snapshots),
            'distribution_count': len(distributions),
            'staleness_days': staleness_days,
            'stale': staleness_days > 90,
        },
    }


def _insufficient_twr(reason):
    return {
        'twr': None,
        'annualized_twr': None,
        'sub_periods': [],
        'data_quality': {'reason': reason, 'stale': True},
    }


# ---------------------------------------------------------------------------
# IRR / XIRR — Internal Rate of Return (T041)
# ---------------------------------------------------------------------------

def calculate_xirr(cash_flows):
    """
    Calculate XIRR (extended internal rate of return) for irregular cash flows.

    Args:
        cash_flows: List of (date, amount) tuples.
                    Negative = money out (investment), positive = money in (return).

    Returns:
        float (annualized rate as decimal, e.g. 0.15 for 15%) or None if
        no solution / insufficient data.
    """
    if len(cash_flows) < 2:
        return None

    # Check for all same sign
    signs = set(1 if cf[1] > 0 else -1 for cf in cash_flows if cf[1] != 0)
    if len(signs) <= 1:
        return None  # Need both positive and negative cash flows

    # Sort by date
    cfs = sorted(cash_flows, key=lambda x: x[0])
    d0 = cfs[0][0]

    # Convert to (fractional_years, amount) using float
    data = []
    for d, amt in cfs:
        t = (d - d0).days / 365.25
        data.append((t, float(amt)))

    # All on the same date?
    if all(t == 0.0 for t, _ in data):
        return None

    def npv(r):
        return sum(amt / (1 + r) ** t for t, amt in data)

    def npv_derivative(r):
        return sum(-amt * t / (1 + r) ** (t + 1) for t, amt in data)

    # Newton's method
    r = 0.10  # initial guess
    for _ in range(100):
        f = npv(r)
        fp = npv_derivative(r)

        if abs(fp) < 1e-15:
            break  # derivative too small, can't continue

        r_new = r - f / fp

        # Clamp to avoid domain errors
        if r_new <= -1.0:
            r_new = -0.99

        if abs(r_new - r) < 1e-10 and abs(f) < 1e-10:
            # Converged — clamp to reasonable range
            return max(-0.99, min(r_new, 10.0))

        r = r_new

    # Fallback: Brent's method (bisection) on [-0.99, 10.0]
    return _brent_xirr(data)


def _brent_xirr(data, lo=-0.99, hi=10.0, tol=1e-10, max_iter=100):
    """Bisection fallback for XIRR when Newton's method fails to converge."""
    def npv(r):
        return sum(amt / (1 + r) ** t for t, amt in data)

    f_lo = npv(lo)
    f_hi = npv(hi)

    # If no sign change in bracket, no solution
    if f_lo * f_hi > 0:
        return None

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = npv(mid)

        if abs(f_mid) < tol or (hi - lo) / 2 < tol:
            return max(-0.99, min(mid, 10.0))

        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid

    return None


def compute_entity_xirr(entity_id, as_of_date=None):
    """
    Compute entity-level XIRR by pooling all cash flows across all assets.
    Capital calls are negative, distributions are positive, terminal residual
    is positive. Returns Decimal percentage (e.g., 15.23) or None.
    """
    from .models import CapitalCall, DistributionAllocation
    from .reports import compute_entity_residual

    if as_of_date is None:
        as_of_date = date.today()

    cash_flows = []

    # Capital calls as negative flows
    calls = CapitalCall.objects.filter(
        commitment__entity_id=entity_id
    )
    for call in calls:
        cash_flows.append((call.call_date, -float(call.amount)))

    # Distributions as positive flows
    allocs = DistributionAllocation.objects.filter(
        entity_id=entity_id
    ).select_related('distribution')
    for alloc in allocs:
        cash_flows.append((alloc.distribution.distribution_date, float(alloc.amount)))

    # Terminal residual as positive flow
    residual = compute_entity_residual(entity_id, as_of_date)
    if residual > 0:
        cash_flows.append((as_of_date, float(residual)))

    if len(cash_flows) < 2:
        return None

    result = calculate_xirr(cash_flows)
    if result is not None:
        return Decimal(str(round(result * 100, 2)))
    return None


def calculate_asset_irr(asset_id, start_date, end_date):
    """
    Calculate IRR for a single asset using FMV snapshots as investment/terminal
    value and distributions as positive cash flows (investor perspective).

    Returns dict with 'irr', 'annualized_irr', 'cash_flow_count'.
    """
    snapshots = list(
        FMVSnapshot.objects.filter(
            asset_id=asset_id,
            snapshot_date__gte=start_date,
            snapshot_date__lte=end_date,
        ).order_by('snapshot_date').values('snapshot_date', 'value')
    )

    if len(snapshots) < 2:
        return {'irr': None, 'annualized_irr': None, 'cash_flow_count': 0, 'reason': 'Insufficient FMV data'}

    distributions = list(
        Distribution.objects.filter(
            asset_id=asset_id,
            distribution_date__gte=start_date,
            distribution_date__lte=end_date,
        ).order_by('distribution_date').values('distribution_date', 'total_amount')
    )

    # Build cash flows (investor perspective)
    cash_flows = []

    # Initial investment: negative (money out)
    first_snap = snapshots[0]
    cash_flows.append((first_snap['snapshot_date'], -float(first_snap['value'])))

    # Distributions: positive (money in to investor)
    for d in distributions:
        cash_flows.append((d['distribution_date'], float(d['total_amount'])))

    # Terminal value: positive (current value the investor could realize)
    last_snap = snapshots[-1]
    cash_flows.append((last_snap['snapshot_date'], float(last_snap['value'])))

    irr = calculate_xirr(cash_flows)

    total_days = (end_date - start_date).days
    annualized = None
    if irr is not None and should_annualize(start_date, end_date):
        # XIRR already returns an annualized rate
        annualized = irr

    return {
        'irr': round(irr * 100, 4) if irr is not None else None,
        'annualized_irr': round(annualized * 100, 4) if annualized is not None else None,
        'cash_flow_count': len(cash_flows),
    }


# ---------------------------------------------------------------------------
# Asset Performance (combined TWR + IRR for all periods)
# ---------------------------------------------------------------------------

def get_asset_performance(asset_id, calc_date=None):
    """
    Calculate performance metrics for an asset across all standard periods.

    Returns dict with metrics per period plus fmv_series.
    """
    calc_date = calc_date or date.today()
    asset = Asset.objects.get(pk=asset_id)

    # Get the inception date (first FMV snapshot)
    first_snap = FMVSnapshot.objects.filter(asset_id=asset_id).order_by('snapshot_date').first()
    inception_date = first_snap.snapshot_date if first_snap else None

    periods = ['ytd', '1y', '3y', 'since_inception']
    metrics = {}

    for period_key in periods:
        start, end, label = resolve_period(period_key, calc_date)
        if period_key == 'since_inception':
            start = inception_date
        if not start:
            metrics[period_key] = {'label': label, 'twr': None, 'irr': None, 'reason': 'No data'}
            continue

        twr_result = calculate_twr(asset_id, start, end)
        irr_result = calculate_asset_irr(asset_id, start, end)

        metrics[period_key] = {
            'label': label,
            'start_date': str(start),
            'end_date': str(end),
            'days': (end - start).days,
            'twr': twr_result.get('twr'),
            'annualized_twr': twr_result.get('annualized_twr'),
            'irr': irr_result.get('irr'),
            'annualized_irr': irr_result.get('annualized_irr'),
            'data_quality': twr_result.get('data_quality', {}),
        }

    # FMV series for chart
    fmv_series = list(
        FMVSnapshot.objects.filter(asset_id=asset_id)
        .order_by('snapshot_date')
        .values('snapshot_date', 'value')
    )
    for s in fmv_series:
        s['value'] = str(s['value'])
        s['snapshot_date'] = str(s['snapshot_date'])

    return {
        'asset_id': asset.id,
        'asset_name': asset.name,
        'metrics': metrics,
        'fmv_series': fmv_series,
    }


# ---------------------------------------------------------------------------
# Entity Performance (ownership-weighted aggregation)
# ---------------------------------------------------------------------------

def get_entity_performance(entity_id, calc_date=None):
    """
    Calculate ownership-weighted TWR and recalculated IRR for an entity's portfolio.
    """
    calc_date = calc_date or date.today()

    ownerships = list(
        EntityAssetOwnership.objects.filter(entity_id=entity_id)
        .select_related('asset')
        .values('asset_id', 'asset__name', 'percentage')
    )

    if not ownerships:
        return {'entity_id': entity_id, 'metrics': {}, 'assets': [], 'reason': 'No asset ownerships'}

    periods = ['ytd', '1y', '3y', 'since_inception']
    metrics = {}

    for period_key in periods:
        start, end, label = resolve_period(period_key, calc_date)

        # For since_inception, find earliest snapshot across all owned assets
        if period_key == 'since_inception':
            asset_ids = [o['asset_id'] for o in ownerships]
            first_snap = (
                FMVSnapshot.objects.filter(asset_id__in=asset_ids)
                .order_by('snapshot_date')
                .first()
            )
            start = first_snap.snapshot_date if first_snap else None

        if not start:
            metrics[period_key] = {'label': label, 'twr': None, 'irr': None}
            continue

        # Value-weighted TWR
        weighted_twr = 0.0
        total_weight = 0.0
        for o in ownerships:
            twr_result = calculate_twr(o['asset_id'], start, end)
            if twr_result['twr'] is not None:
                # Weight = beginning-of-period FMV × ownership %
                first_fmv = (
                    FMVSnapshot.objects.filter(
                        asset_id=o['asset_id'],
                        snapshot_date__lte=start,
                    ).order_by('-snapshot_date').first()
                )
                if not first_fmv:
                    first_fmv = (
                        FMVSnapshot.objects.filter(
                            asset_id=o['asset_id'],
                            snapshot_date__gte=start,
                        ).order_by('snapshot_date').first()
                    )
                if first_fmv:
                    weight = float(first_fmv.value) * float(o['percentage']) / 100
                    weighted_twr += weight * twr_result['twr']
                    total_weight += weight

        portfolio_twr = weighted_twr / total_weight if total_weight > 0 else None

        # Recalculated IRR from combined cash flows
        combined_cfs = []
        for o in ownerships:
            pct = float(o['percentage']) / 100
            snaps = list(
                FMVSnapshot.objects.filter(
                    asset_id=o['asset_id'],
                    snapshot_date__gte=start,
                    snapshot_date__lte=end,
                ).order_by('snapshot_date').values('snapshot_date', 'value')
            )
            if len(snaps) >= 2:
                # Initial investment (scaled)
                combined_cfs.append((snaps[0]['snapshot_date'], -float(snaps[0]['value']) * pct))
                # Terminal value (scaled)
                combined_cfs.append((snaps[-1]['snapshot_date'], float(snaps[-1]['value']) * pct))

            # Distributions scaled by entity allocation
            from .models import DistributionAllocation
            allocs = DistributionAllocation.objects.filter(
                entity_id=entity_id,
                distribution__asset_id=o['asset_id'],
                distribution__distribution_date__gte=start,
                distribution__distribution_date__lte=end,
            ).select_related('distribution').values(
                'distribution__distribution_date', 'amount'
            )
            for a in allocs:
                combined_cfs.append((a['distribution__distribution_date'], float(a['amount'])))

        portfolio_irr = calculate_xirr(combined_cfs) if combined_cfs else None

        total_days = (end - start).days
        metrics[period_key] = {
            'label': label,
            'start_date': str(start),
            'end_date': str(end),
            'days': total_days,
            'twr': round(portfolio_twr, 4) if portfolio_twr is not None else None,
            'irr': round(portfolio_irr * 100, 4) if portfolio_irr is not None else None,
        }

    # Asset breakdown
    asset_breakdown = []
    for o in ownerships:
        latest_fmv = FMVSnapshot.objects.filter(asset_id=o['asset_id']).order_by('-snapshot_date').first()
        asset_breakdown.append({
            'asset_id': o['asset_id'],
            'asset_name': o['asset__name'],
            'ownership_pct': float(o['percentage']),
            'current_fmv': str(latest_fmv.value) if latest_fmv else None,
            'entity_share': str(
                latest_fmv.value * o['percentage'] / 100
            ) if latest_fmv else None,
        })

    return {
        'entity_id': entity_id,
        'metrics': metrics,
        'assets': asset_breakdown,
    }


# ---------------------------------------------------------------------------
# Performance Summary (portfolio-wide)
# ---------------------------------------------------------------------------

def get_performance_summary(calc_date=None):
    """
    Portfolio-wide performance summary with total, by-asset-type,
    and top/bottom performers.
    """
    calc_date = calc_date or date.today()

    assets = Asset.objects.prefetch_related('fmv_snapshots').all()
    results = []

    for asset in assets:
        latest = asset.fmv_snapshots.order_by('-snapshot_date').first()
        if not latest:
            continue

        # YTD TWR as the primary metric
        start = date(calc_date.year, 1, 1)
        twr_result = calculate_twr(asset.id, start, calc_date)

        results.append({
            'asset_id': asset.id,
            'asset_name': asset.name,
            'asset_type': asset.asset_type,
            'current_fmv': str(latest.value),
            'ytd_twr': twr_result.get('twr'),
        })

    # Sort by YTD TWR for top/bottom
    with_twr = [r for r in results if r['ytd_twr'] is not None]
    with_twr.sort(key=lambda x: x['ytd_twr'], reverse=True)

    # Group by asset type
    by_type = defaultdict(lambda: {'count': 0, 'total_fmv': 0})
    for r in results:
        t = r['asset_type']
        by_type[t]['count'] += 1
        by_type[t]['total_fmv'] += float(r['current_fmv'])

    return {
        'total_assets': len(results),
        'total_fmv': str(sum(float(r['current_fmv']) for r in results)),
        'by_asset_type': dict(by_type),
        'top_performers': with_twr[:5],
        'bottom_performers': with_twr[-5:][::-1] if len(with_twr) > 5 else [],
        'all_assets': results,
    }
