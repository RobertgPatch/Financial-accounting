from decimal import Decimal
from datetime import date
from django.db.models import Sum, Count, Avg, F, Q
from .models import Distribution, DistributionAllocation, Entity, Asset, EntityAssetOwnership, Budget, BudgetLineItem, FMVSnapshot


# ═══════════════════════════════════════════════════════════════════════
# FMV Report constants and generation
# ═══════════════════════════════════════════════════════════════════════

PLAID_TYPE_MAP = {
    'depository': 'cash',
    'investment': 'public_equity',
    'loan': 'fixed_income',
    'credit': 'cash',
}

ASSET_TYPE_LABELS = {
    'cash': 'Cash & Equivalents',
    'real_estate': 'Real Estate',
    'public_equity': 'Public Equity',
    'private_equity': 'Private Equity',
    'fixed_income': 'Fixed Income',
    'hedge_fund': 'Hedge Fund',
    'crypto': 'Cryptocurrency',
    'collectible': 'Collectible',
    'other': 'Other',
}


def _collect_valued_items(entity_ids=None, type_filters=None):
    """
    Collect all valued items from Plaid accounts and manual FMV snapshots.
    Handles dedup (mapped assets not double-counted), entity filtering,
    and type filtering. Returns list of dicts with Decimal 'value' fields
    (NOT string-encoded — caller decides serialization).
    """
    from plaid_integration.models import PlaidAccount

    # Step 1: Query all Plaid accounts with related data
    plaid_accounts = PlaidAccount.objects.select_related('plaid_item', 'asset').all()
    mapped_asset_ids = set(pa.asset_id for pa in plaid_accounts if pa.asset_id)

    # Step 2: Build items from Plaid accounts
    plaid_items = []
    for pa in plaid_accounts:
        if pa.asset_id:
            asset_type = pa.asset.asset_type
        else:
            asset_type = PLAID_TYPE_MAP.get(pa.type, 'other')
        label = ASSET_TYPE_LABELS.get(asset_type, 'Other')
        balance = pa.current_balance if pa.current_balance is not None else Decimal('0.00')
        needs_sync = pa.current_balance is None

        plaid_items.append({
            'name': pa.name,
            'value': balance,
            'source': 'plaid',
            'asset_type': asset_type,
            'label': label,
            'asset_id': pa.asset_id,
            'snapshot_date': None,
            'institution': pa.plaid_item.institution_name if pa.plaid_item else None,
            'subtype': pa.subtype,
            'plaid_account_id': pa.id,
            'mask': pa.mask,
            'needs_sync': needs_sync,
        })

    # Step 3: Query manual assets with FMV snapshots, excluding mapped ones
    manual_assets = Asset.objects.filter(
        fmv_snapshots__isnull=False,
    ).exclude(
        id__in=mapped_asset_ids,
    ).distinct()

    manual_items = []
    for asset in manual_assets:
        latest_snapshot = asset.fmv_snapshots.order_by('-snapshot_date').first()
        if latest_snapshot:
            manual_items.append({
                'name': asset.name,
                'value': latest_snapshot.value,
                'source': 'manual',
                'asset_type': asset.asset_type,
                'label': ASSET_TYPE_LABELS.get(asset.asset_type, 'Other'),
                'asset_id': asset.id,
                'snapshot_date': str(latest_snapshot.snapshot_date),
                'institution': None,
                'subtype': None,
                'plaid_account_id': None,
                'mask': None,
                'needs_sync': False,
            })

    # Step 4: Apply entity filter
    if entity_ids:
        owned_asset_ids = set(
            EntityAssetOwnership.objects.filter(
                entity_id__in=entity_ids,
            ).values_list('asset_id', flat=True)
        )
        manual_items = [item for item in manual_items if item['asset_id'] in owned_asset_ids]
        plaid_items = [
            item for item in plaid_items
            if item['asset_id'] and item['asset_id'] in owned_asset_ids
        ]

    items = plaid_items + manual_items

    # Step 5: Apply type filters
    if type_filters:
        items = [item for item in items if item['asset_type'] in type_filters]

    return items


def generate_fmv_report(type_filters=None, entity_ids=None):
    """
    Generate a consolidated FMV report combining Plaid account balances
    and manual asset FMV snapshots.
    """
    items = _collect_valued_items(entity_ids=entity_ids, type_filters=type_filters)

    # Aggregate by type
    type_totals = {}
    total_fmv = Decimal('0.00')

    for item in items:
        total_fmv += item['value']
        t = item['asset_type']
        if t not in type_totals:
            type_totals[t] = {
                'asset_type': t,
                'label': item['label'],
                'total_value': Decimal('0.00'),
                'count': 0,
            }
        type_totals[t]['total_value'] += item['value']
        type_totals[t]['count'] += 1

    by_type = []
    for t_data in sorted(type_totals.values(), key=lambda x: -x['total_value']):
        pct = (t_data['total_value'] / total_fmv * 100) if total_fmv != 0 else Decimal('0.00')
        by_type.append({
            'asset_type': t_data['asset_type'],
            'label': t_data['label'],
            'total_value': str(t_data['total_value']),
            'count': t_data['count'],
            'percentage': str(pct.quantize(Decimal('0.01'))),
        })

    # Convert item values to string for JSON serialization
    for item in items:
        item['value'] = str(item['value'])

    return {
        'total_fmv': str(total_fmv),
        'item_count': len(items),
        'filters': {
            'type_filters': type_filters or [],
            'entity_ids': [int(eid) for eid in entity_ids] if entity_ids else [],
        },
        'by_type': by_type,
        'items': items,
    }


# ═══════════════════════════════════════════════════════════════════════
# Portfolio Tracker helpers
# ═══════════════════════════════════════════════════════════════════════

def compute_entity_residual(entity_id, as_of_date=None):
    """
    Compute total residual value for an entity across all owned assets.
    For each asset owned by the entity via EntityAssetOwnership:
      - Plaid-mapped: use PlaidAccount.current_balance
      - Manual: use latest FMVSnapshot.value (on or before as_of_date if given)
    Multiply by ownership percentage / 100, sum all.
    Returns Decimal.
    """
    from plaid_integration.models import PlaidAccount

    ownerships = EntityAssetOwnership.objects.filter(
        entity_id=entity_id
    ).select_related('asset')

    # Build a map of asset_id → PlaidAccount balance for mapped assets
    plaid_accounts = PlaidAccount.objects.select_related('asset').filter(
        asset__isnull=False
    )
    plaid_balance_map = {}
    for pa in plaid_accounts:
        if pa.asset_id and pa.current_balance is not None:
            plaid_balance_map[pa.asset_id] = pa.current_balance

    total_residual = Decimal('0.00')
    for ownership in ownerships:
        asset_id = ownership.asset_id
        pct = ownership.percentage

        # Prefer Plaid balance for mapped assets
        if asset_id in plaid_balance_map:
            asset_value = plaid_balance_map[asset_id]
        else:
            # Use latest FMV snapshot
            snapshots = FMVSnapshot.objects.filter(asset_id=asset_id)
            if as_of_date:
                snapshots = snapshots.filter(snapshot_date__lte=as_of_date)
            latest = snapshots.order_by('-snapshot_date').first()
            asset_value = latest.value if latest else Decimal('0.00')

        entity_share = asset_value * pct / Decimal('100')
        total_residual += entity_share

    return total_residual


def generate_portfolio_summary(entity_ids=None, as_of_date=None, start_date=None, end_date=None):
    """Generate Portfolio Summary with entity rollups and PE/VC metrics."""
    from .models import Commitment, CapitalCall
    from .performance import compute_entity_xirr

    if as_of_date is None:
        as_of_date = end_date or date.today()

    # Get entities to include
    if entity_ids:
        entities = Entity.objects.filter(id__in=entity_ids).order_by('name')
    else:
        entities = Entity.objects.all().order_by('name')

    entity_rows = []
    # Accumulators for "All Entities" row
    total_original = Decimal('0.00')
    total_paid_in = Decimal('0.00')
    total_distributions = Decimal('0.00')
    total_residual = Decimal('0.00')

    for entity in entities:
        # Commitment aggregates
        commitments = Commitment.objects.filter(entity=entity)
        original_commitment = commitments.aggregate(
            total=Sum('original_amount')
        )['total'] or Decimal('0.00')

        # Paid-in from capital calls (filtered by date range)
        calls_qs = CapitalCall.objects.filter(commitment__entity=entity)
        if start_date:
            calls_qs = calls_qs.filter(call_date__gte=start_date)
        if end_date:
            calls_qs = calls_qs.filter(call_date__lte=end_date)
        paid_in = calls_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # % Called and Unfunded
        if original_commitment > 0:
            pct_called = (paid_in / original_commitment * 100).quantize(Decimal('0.01'))
            unfunded = original_commitment - paid_in
        else:
            pct_called = None
            unfunded = Decimal('0.00')

        # Distributions from DistributionAllocation (filtered by date range)
        dist_qs = DistributionAllocation.objects.filter(entity=entity)
        if start_date:
            dist_qs = dist_qs.filter(distribution__distribution_date__gte=start_date)
        if end_date:
            dist_qs = dist_qs.filter(distribution__distribution_date__lte=end_date)
        distributions = dist_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Residual value
        residual = compute_entity_residual(entity.id, as_of_date)

        # PE metrics
        if paid_in > 0:
            dpi = (distributions / paid_in).quantize(Decimal('0.01'))
            rvpi = (residual / paid_in).quantize(Decimal('0.01'))
            tvpi = ((distributions + residual) / paid_in).quantize(Decimal('0.01'))
        else:
            dpi = None
            rvpi = None
            tvpi = None

        # IRR
        irr = compute_entity_xirr(entity.id, as_of_date, start_date=start_date, end_date=end_date)

        entity_rows.append({
            'entity_id': entity.id,
            'entity_name': entity.name,
            'entity_type': entity.entity_type,
            'original_commitment': str(original_commitment.quantize(Decimal('0.01'))),
            'pct_called': str(pct_called) if pct_called is not None else None,
            'unfunded_commitment': str(unfunded.quantize(Decimal('0.01'))),
            'paid_in': str(paid_in.quantize(Decimal('0.01'))),
            'distributions': str(distributions.quantize(Decimal('0.01'))),
            'residual': str(residual.quantize(Decimal('0.01'))),
            'dpi': str(dpi) if dpi is not None else None,
            'rvpi': str(rvpi) if rvpi is not None else None,
            'tvpi': str(tvpi) if tvpi is not None else None,
            'irr': str(irr) if irr is not None else None,
        })

        total_original += original_commitment
        total_paid_in += paid_in
        total_distributions += distributions
        total_residual += residual

    # "All Entities" row — recompute ratios from aggregates
    if total_paid_in > 0:
        all_dpi = (total_distributions / total_paid_in).quantize(Decimal('0.01'))
        all_rvpi = (total_residual / total_paid_in).quantize(Decimal('0.01'))
        all_tvpi = ((total_distributions + total_residual) / total_paid_in).quantize(Decimal('0.01'))
    else:
        all_dpi = None
        all_rvpi = None
        all_tvpi = None

    if total_original > 0:
        all_pct_called = (total_paid_in / total_original * 100).quantize(Decimal('0.01'))
    else:
        all_pct_called = None

    # All-entities IRR: pool ALL cash flows across ALL entities
    all_entity_ids = [e.id for e in entities]
    all_irr = _compute_pooled_xirr(all_entity_ids, as_of_date, start_date=start_date, end_date=end_date)

    all_entities_row = {
        'original_commitment': str(total_original.quantize(Decimal('0.01'))),
        'pct_called': str(all_pct_called) if all_pct_called is not None else None,
        'unfunded_commitment': str((total_original - total_paid_in).quantize(Decimal('0.01'))),
        'paid_in': str(total_paid_in.quantize(Decimal('0.01'))),
        'distributions': str(total_distributions.quantize(Decimal('0.01'))),
        'residual': str(total_residual.quantize(Decimal('0.01'))),
        'dpi': str(all_dpi) if all_dpi is not None else None,
        'rvpi': str(all_rvpi) if all_rvpi is not None else None,
        'tvpi': str(all_tvpi) if all_tvpi is not None else None,
        'irr': str(all_irr) if all_irr is not None else None,
    }

    return {
        'as_of_date': str(as_of_date),
        'entities': entity_rows,
        'all_entities': all_entities_row,
        'filters': {
            'entity_ids': [int(eid) for eid in entity_ids] if entity_ids else [],
            'as_of_date': str(as_of_date),
        },
    }


def _compute_pooled_xirr(entity_ids, as_of_date, start_date=None, end_date=None):
    """Pool cash flows from multiple entities and compute a single XIRR."""
    from .models import CapitalCall
    from .performance import calculate_xirr

    cash_flows = []

    # Capital calls as negative flows
    calls = CapitalCall.objects.filter(
        commitment__entity_id__in=entity_ids
    ).select_related('commitment')
    if start_date:
        calls = calls.filter(call_date__gte=start_date)
    if end_date:
        calls = calls.filter(call_date__lte=end_date)
    for call in calls:
        cash_flows.append((call.call_date, -float(call.amount)))

    # Distributions as positive flows
    allocs = DistributionAllocation.objects.filter(
        entity_id__in=entity_ids
    ).select_related('distribution')
    if start_date:
        allocs = allocs.filter(distribution__distribution_date__gte=start_date)
    if end_date:
        allocs = allocs.filter(distribution__distribution_date__lte=end_date)
    for alloc in allocs:
        cash_flows.append((alloc.distribution.distribution_date, float(alloc.amount)))

    # Terminal residual as positive flow
    total_residual = sum(
        compute_entity_residual(eid, as_of_date) for eid in entity_ids
    )
    if total_residual > 0:
        cash_flows.append((as_of_date, float(total_residual)))

    if len(cash_flows) < 2:
        return None

    result = calculate_xirr(cash_flows)
    if result is not None:
        return Decimal(str(round(result * 100, 2)))
    return None


def _compute_asset_class_xirr(asset_type, entity_ids, as_of_date, start_date=None, end_date=None):
    """Compute pooled XIRR for all commitments of a given asset_type."""
    from .models import Commitment, CapitalCall
    from .performance import calculate_xirr

    commitments = Commitment.objects.filter(asset__asset_type=asset_type).select_related('asset')
    if entity_ids:
        commitments = commitments.filter(entity_id__in=entity_ids)

    cash_flows = []
    for commitment in commitments:
        calls_qs = commitment.capital_calls.all()
        if start_date:
            calls_qs = calls_qs.filter(call_date__gte=start_date)
        if end_date:
            calls_qs = calls_qs.filter(call_date__lte=end_date)
        for call in calls_qs:
            cash_flows.append((call.call_date, -float(call.amount)))

    allocs = DistributionAllocation.objects.filter(
        distribution__asset__asset_type=asset_type
    ).select_related('distribution')
    if entity_ids:
        allocs = allocs.filter(entity_id__in=entity_ids)
    if start_date:
        allocs = allocs.filter(distribution__distribution_date__gte=start_date)
    if end_date:
        allocs = allocs.filter(distribution__distribution_date__lte=end_date)
    for alloc in allocs:
        cash_flows.append((alloc.distribution.distribution_date, float(alloc.amount)))

    # Terminal residual
    from plaid_integration.models import PlaidAccount
    plaid_balance_map = {}
    for pa in PlaidAccount.objects.filter(asset__isnull=False, asset__asset_type=asset_type):
        if pa.asset_id and pa.current_balance is not None:
            plaid_balance_map[pa.asset_id] = pa.current_balance

    ownerships = EntityAssetOwnership.objects.filter(
        asset__asset_type=asset_type
    ).select_related('asset')
    if entity_ids:
        ownerships = ownerships.filter(entity_id__in=entity_ids)

    total_residual = Decimal('0.00')
    for ownership in ownerships:
        aid = ownership.asset_id
        if aid in plaid_balance_map:
            asset_value = plaid_balance_map[aid]
        else:
            snaps = FMVSnapshot.objects.filter(asset_id=aid)
            if as_of_date:
                snaps = snaps.filter(snapshot_date__lte=as_of_date)
            latest = snaps.order_by('-snapshot_date').first()
            asset_value = latest.value if latest else Decimal('0.00')
        total_residual += asset_value * ownership.percentage / Decimal('100')

    if total_residual > 0:
        cash_flows.append((as_of_date, float(total_residual)))

    if len(cash_flows) < 2:
        return None
    result = calculate_xirr(cash_flows)
    if result is not None:
        return Decimal(str(round(result * 100, 2)))
    return None


def generate_asset_class_summary(entity_ids=None, type_filters=None, as_of_date=None, start_date=None, end_date=None):
    """Generate Asset Class Summary — same columns as Portfolio Summary but grouped by asset type."""
    from .models import Commitment, CapitalCall

    if as_of_date is None:
        as_of_date = end_date or date.today()

    # Determine which asset types have data
    commitments = Commitment.objects.select_related('asset').all()
    if entity_ids:
        commitments = commitments.filter(entity_id__in=entity_ids)
    if type_filters:
        commitments = commitments.filter(asset__asset_type__in=type_filters)

    # Group by asset_type
    class_data = {}  # asset_type -> accumulators
    for commitment in commitments:
        atype = commitment.asset.asset_type
        if atype not in class_data:
            class_data[atype] = {
                'original_commitment': Decimal('0.00'),
                'paid_in': Decimal('0.00'),
                'distributions': Decimal('0.00'),
                'residual': Decimal('0.00'),
            }
        cd = class_data[atype]
        cd['original_commitment'] += commitment.original_amount

        # Paid-in from capital calls
        calls_qs = commitment.capital_calls
        if start_date:
            calls_qs = calls_qs.filter(call_date__gte=start_date)
        if end_date:
            calls_qs = calls_qs.filter(call_date__lte=end_date)
        calls_total = calls_qs.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        cd['paid_in'] += calls_total

        # Distributions for this entity-asset pair
        dist_qs = DistributionAllocation.objects.filter(
            entity=commitment.entity,
            distribution__asset=commitment.asset,
        )
        if start_date:
            dist_qs = dist_qs.filter(distribution__distribution_date__gte=start_date)
        if end_date:
            dist_qs = dist_qs.filter(distribution__distribution_date__lte=end_date)
        dist_total = dist_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        cd['distributions'] += dist_total

        # Residual for this entity-asset pair
        ownership = EntityAssetOwnership.objects.filter(
            entity=commitment.entity, asset=commitment.asset
        ).first()
        pct = ownership.percentage if ownership else Decimal('0')

        from plaid_integration.models import PlaidAccount
        plaid_acct = PlaidAccount.objects.filter(asset=commitment.asset).first()
        if plaid_acct and plaid_acct.current_balance is not None:
            asset_value = plaid_acct.current_balance
        else:
            snap = FMVSnapshot.objects.filter(asset=commitment.asset)
            if as_of_date:
                snap = snap.filter(snapshot_date__lte=as_of_date)
            latest = snap.order_by('-snapshot_date').first()
            asset_value = latest.value if latest else Decimal('0.00')
        cd['residual'] += asset_value * pct / Decimal('100')

    # Build rows
    rows = []
    total_original = Decimal('0.00')
    total_paid_in = Decimal('0.00')
    total_distributions = Decimal('0.00')
    total_residual = Decimal('0.00')

    for atype in sorted(class_data.keys(), key=lambda t: -class_data[t]['original_commitment']):
        cd = class_data[atype]
        oc = cd['original_commitment']
        pi = cd['paid_in']
        dist = cd['distributions']
        res = cd['residual']

        if oc > 0:
            pct_called = (pi / oc * 100).quantize(Decimal('0.01'))
            unfunded = oc - pi
        else:
            pct_called = None
            unfunded = Decimal('0.00')

        if pi > 0:
            dpi = (dist / pi).quantize(Decimal('0.01'))
            rvpi = (res / pi).quantize(Decimal('0.01'))
            tvpi = ((dist + res) / pi).quantize(Decimal('0.01'))
        else:
            dpi = None
            rvpi = None
            tvpi = None

        irr = _compute_asset_class_xirr(atype, entity_ids, as_of_date, start_date=start_date, end_date=end_date)

        rows.append({
            'asset_class': ASSET_TYPE_LABELS.get(atype, atype),
            'asset_type': atype,
            'original_commitment': str(oc.quantize(Decimal('0.01'))),
            'pct_called': str(pct_called) if pct_called is not None else None,
            'unfunded_commitment': str(unfunded.quantize(Decimal('0.01'))),
            'paid_in': str(pi.quantize(Decimal('0.01'))),
            'distributions': str(dist.quantize(Decimal('0.01'))),
            'residual': str(res.quantize(Decimal('0.01'))),
            'dpi': str(dpi) if dpi is not None else None,
            'rvpi': str(rvpi) if rvpi is not None else None,
            'tvpi': str(tvpi) if tvpi is not None else None,
            'irr': str(irr) if irr is not None else None,
        })

        total_original += oc
        total_paid_in += pi
        total_distributions += dist
        total_residual += res

    # All Classes total row
    if total_paid_in > 0:
        all_dpi = (total_distributions / total_paid_in).quantize(Decimal('0.01'))
        all_rvpi = (total_residual / total_paid_in).quantize(Decimal('0.01'))
        all_tvpi = ((total_distributions + total_residual) / total_paid_in).quantize(Decimal('0.01'))
    else:
        all_dpi = None
        all_rvpi = None
        all_tvpi = None

    if total_original > 0:
        all_pct_called = (total_paid_in / total_original * 100).quantize(Decimal('0.01'))
    else:
        all_pct_called = None

    # Pooled IRR across all types
    all_entity_ids = list(entity_ids) if entity_ids else list(
        Entity.objects.values_list('id', flat=True)
    )
    all_irr = _compute_pooled_xirr(all_entity_ids, as_of_date, start_date=start_date, end_date=end_date)

    all_classes_row = {
        'original_commitment': str(total_original.quantize(Decimal('0.01'))),
        'pct_called': str(all_pct_called) if all_pct_called is not None else None,
        'unfunded_commitment': str((total_original - total_paid_in).quantize(Decimal('0.01'))),
        'paid_in': str(total_paid_in.quantize(Decimal('0.01'))),
        'distributions': str(total_distributions.quantize(Decimal('0.01'))),
        'residual': str(total_residual.quantize(Decimal('0.01'))),
        'dpi': str(all_dpi) if all_dpi is not None else None,
        'rvpi': str(all_rvpi) if all_rvpi is not None else None,
        'tvpi': str(all_tvpi) if all_tvpi is not None else None,
        'irr': str(all_irr) if all_irr is not None else None,
    }

    return {
        'as_of_date': str(as_of_date),
        'rows': rows,
        'all_classes': all_classes_row,
        'filters': {
            'entity_ids': [int(eid) for eid in entity_ids] if entity_ids else [],
            'type_filters': type_filters or [],
        },
    }


def generate_investment_performance(entity_ids=None, as_of_date=None, start_date=None, end_date=None):
    """Generate Investment Performance view — per-asset and per-entity metrics."""
    from .models import Commitment, CapitalCall
    from .performance import calculate_xirr, compute_entity_xirr

    if as_of_date is None:
        as_of_date = end_date or date.today()

    # Get commitments (optionally filtered by entity)
    commitments = Commitment.objects.select_related('entity', 'asset').all()
    if entity_ids:
        commitments = commitments.filter(entity_id__in=entity_ids)

    investments = []
    entity_data = {}  # entity_id -> accumulated data

    for commitment in commitments:
        entity = commitment.entity
        asset = commitment.asset

        # Per-asset paid-in
        calls_qs = commitment.capital_calls
        if start_date:
            calls_qs = calls_qs.filter(call_date__gte=start_date)
        if end_date:
            calls_qs = calls_qs.filter(call_date__lte=end_date)
        paid_in = calls_qs.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Per-asset distributions
        dist_qs = DistributionAllocation.objects.filter(
            entity=entity,
            distribution__asset=asset,
        )
        if start_date:
            dist_qs = dist_qs.filter(distribution__distribution_date__gte=start_date)
        if end_date:
            dist_qs = dist_qs.filter(distribution__distribution_date__lte=end_date)
        distributions = dist_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Per-asset residual (pro-rated by ownership)
        ownership = EntityAssetOwnership.objects.filter(
            entity=entity, asset=asset
        ).first()
        pct = ownership.percentage if ownership else Decimal('0')

        # Get asset value (Plaid or FMV)
        from plaid_integration.models import PlaidAccount
        plaid_acct = PlaidAccount.objects.filter(asset=asset).first()
        if plaid_acct and plaid_acct.current_balance is not None:
            asset_value = plaid_acct.current_balance
        else:
            snap = FMVSnapshot.objects.filter(asset=asset)
            if as_of_date:
                snap = snap.filter(snapshot_date__lte=as_of_date)
            latest = snap.order_by('-snapshot_date').first()
            asset_value = latest.value if latest else Decimal('0.00')

        residual = asset_value * pct / Decimal('100')

        # Per-asset ratios
        if paid_in > 0:
            dpi = (distributions / paid_in).quantize(Decimal('0.01'))
            rvpi = (residual / paid_in).quantize(Decimal('0.01'))
            tvpi = ((distributions + residual) / paid_in).quantize(Decimal('0.01'))
        else:
            dpi = None
            rvpi = None
            tvpi = None

        # Per-asset IRR
        asset_cash_flows = []
        irr_calls = commitment.capital_calls.all()
        if start_date:
            irr_calls = irr_calls.filter(call_date__gte=start_date)
        if end_date:
            irr_calls = irr_calls.filter(call_date__lte=end_date)
        for call in irr_calls:
            asset_cash_flows.append((call.call_date, -float(call.amount)))
        asset_allocs = DistributionAllocation.objects.filter(
            entity=entity, distribution__asset=asset,
        ).select_related('distribution')
        if start_date:
            asset_allocs = asset_allocs.filter(distribution__distribution_date__gte=start_date)
        if end_date:
            asset_allocs = asset_allocs.filter(distribution__distribution_date__lte=end_date)
        for alloc in asset_allocs:
            asset_cash_flows.append((alloc.distribution.distribution_date, float(alloc.amount)))
        if residual > 0:
            asset_cash_flows.append((as_of_date, float(residual)))

        asset_irr = None
        if len(asset_cash_flows) >= 2:
            result = calculate_xirr(asset_cash_flows)
            if result is not None:
                asset_irr = Decimal(str(round(result * 100, 2)))

        # % Called and Unfunded
        orig = commitment.original_amount
        if orig > 0:
            inv_pct_called = (paid_in / orig * 100).quantize(Decimal('0.01'))
            inv_unfunded = orig - paid_in
        else:
            inv_pct_called = None
            inv_unfunded = Decimal('0.00')

        investments.append({
            'asset_id': asset.id,
            'asset_name': asset.name,
            'asset_type': asset.asset_type,
            'entity_id': entity.id,
            'entity_name': entity.name,
            'original_commitment': str(commitment.original_amount.quantize(Decimal('0.01'))),
            'pct_called': str(inv_pct_called) if inv_pct_called is not None else None,
            'unfunded_commitment': str(inv_unfunded.quantize(Decimal('0.01'))),
            'paid_in': str(paid_in.quantize(Decimal('0.01'))),
            'distributions': str(distributions.quantize(Decimal('0.01'))),
            'residual': str(residual.quantize(Decimal('0.01'))),
            'dpi': str(dpi) if dpi is not None else None,
            'rvpi': str(rvpi) if rvpi is not None else None,
            'tvpi': str(tvpi) if tvpi is not None else None,
            'irr': str(asset_irr) if asset_irr is not None else None,
        })

        # Accumulate for entity totals
        eid = entity.id
        if eid not in entity_data:
            entity_data[eid] = {
                'entity_id': eid,
                'entity_name': entity.name,
                'original_commitment': Decimal('0.00'),
                'paid_in': Decimal('0.00'),
                'distributions': Decimal('0.00'),
                'residual': Decimal('0.00'),
            }
        entity_data[eid]['original_commitment'] += commitment.original_amount
        entity_data[eid]['paid_in'] += paid_in
        entity_data[eid]['distributions'] += distributions
        entity_data[eid]['residual'] += residual

    # Build entity_totals with pooled XIRR
    entity_totals = []
    for eid, edata in sorted(entity_data.items(), key=lambda x: x[1]['entity_name']):
        eoc = edata['original_commitment']
        ep = edata['paid_in']
        ed = edata['distributions']
        er = edata['residual']

        if eoc > 0:
            e_pct_called = (ep / eoc * 100).quantize(Decimal('0.01'))
            e_unfunded = eoc - ep
        else:
            e_pct_called = None
            e_unfunded = Decimal('0.00')

        if ep > 0:
            e_dpi = (ed / ep).quantize(Decimal('0.01'))
            e_rvpi = (er / ep).quantize(Decimal('0.01'))
            e_tvpi = ((ed + er) / ep).quantize(Decimal('0.01'))
        else:
            e_dpi = None
            e_rvpi = None
            e_tvpi = None

        e_irr = compute_entity_xirr(eid, as_of_date, start_date=start_date, end_date=end_date)

        entity_totals.append({
            'entity_id': eid,
            'entity_name': edata['entity_name'],
            'original_commitment': str(eoc.quantize(Decimal('0.01'))),
            'pct_called': str(e_pct_called) if e_pct_called is not None else None,
            'unfunded_commitment': str(e_unfunded.quantize(Decimal('0.01'))),
            'paid_in': str(ep.quantize(Decimal('0.01'))),
            'distributions': str(ed.quantize(Decimal('0.01'))),
            'residual': str(er.quantize(Decimal('0.01'))),
            'dpi': str(e_dpi) if e_dpi is not None else None,
            'rvpi': str(e_rvpi) if e_rvpi is not None else None,
            'tvpi': str(e_tvpi) if e_tvpi is not None else None,
            'irr': str(e_irr) if e_irr is not None else None,
        })

    return {
        'as_of_date': str(as_of_date),
        'investments': investments,
        'entity_totals': entity_totals,
        'filters': {
            'entity_ids': [int(eid) for eid in entity_ids] if entity_ids else [],
            'as_of_date': str(as_of_date),
        },
    }


def generate_distribution_report(
    period_type='yearly',
    year=None,
    quarter=None,
    month=None,
    entity_ids=None,
    asset_ids=None,
):
    if year is None:
        year = date.today().year

    distributions = Distribution.objects.select_related('asset').all()

    # Filter by period
    distributions = distributions.filter(distribution_date__year=year)
    if period_type == 'quarterly' and quarter:
        quarter_months = {1: [1,2,3], 2: [4,5,6], 3: [7,8,9], 4: [10,11,12]}
        months = quarter_months.get(quarter, [])
        distributions = distributions.filter(distribution_date__month__in=months)
    elif period_type == 'monthly' and month:
        distributions = distributions.filter(distribution_date__month=month)

    # Filter by asset
    if asset_ids:
        distributions = distributions.filter(asset_id__in=asset_ids)

    allocations = DistributionAllocation.objects.filter(
        distribution__in=distributions
    ).select_related('entity', 'distribution', 'distribution__asset')

    # Filter by entity
    if entity_ids:
        allocations = allocations.filter(entity_id__in=entity_ids)

    # Aggregate by entity
    entity_summary = {}
    for alloc in allocations:
        eid = alloc.entity_id
        if eid not in entity_summary:
            entity_summary[eid] = {
                'entity_id': eid,
                'entity_name': alloc.entity.name,
                'entity_type': alloc.entity.entity_type,
                'total_amount': Decimal('0.00'),
                'distribution_count': 0,
                'by_asset': {},
            }
        entity_summary[eid]['total_amount'] += alloc.amount
        entity_summary[eid]['distribution_count'] += 1

        aid = alloc.distribution.asset_id
        if aid not in entity_summary[eid]['by_asset']:
            entity_summary[eid]['by_asset'][aid] = {
                'asset_id': aid,
                'asset_name': alloc.distribution.asset.name,
                'asset_type': alloc.distribution.asset.asset_type,
                'total_amount': Decimal('0.00'),
                'distribution_count': 0,
            }
        entity_summary[eid]['by_asset'][aid]['total_amount'] += alloc.amount
        entity_summary[eid]['by_asset'][aid]['distribution_count'] += 1

    # Aggregate by asset (based on allocations to stay consistent with entity filter)
    asset_summary = {}
    asset_distribution_ids = {}
    for alloc in allocations:
        aid = alloc.distribution.asset_id
        if aid not in asset_summary:
            asset_summary[aid] = {
                'asset_id': aid,
                'asset_name': alloc.distribution.asset.name,
                'asset_type': alloc.distribution.asset.asset_type,
                'total_amount': Decimal('0.00'),
                'distribution_count': 0,
            }
            asset_distribution_ids[aid] = set()
        asset_summary[aid]['total_amount'] += alloc.amount
        if alloc.distribution_id not in asset_distribution_ids[aid]:
            asset_distribution_ids[aid].add(alloc.distribution_id)
            asset_summary[aid]['distribution_count'] += 1

    # Build detail list
    detail = []
    for alloc in allocations:
        detail.append({
            'distribution_id': alloc.distribution_id,
            'distribution_date': str(alloc.distribution.distribution_date),
            'distribution_type': alloc.distribution.distribution_type,
            'asset_id': alloc.distribution.asset_id,
            'asset_name': alloc.distribution.asset.name,
            'entity_id': alloc.entity_id,
            'entity_name': alloc.entity.name,
            'amount': str(alloc.amount),
            'percentage': str(alloc.percentage),
        })

    total = sum(a['total_amount'] for a in entity_summary.values())

    # Convert Decimals to strings for JSON
    for e in entity_summary.values():
        e['total_amount'] = str(e['total_amount'])
        for a in e['by_asset'].values():
            a['total_amount'] = str(a['total_amount'])
        e['by_asset'] = list(e['by_asset'].values())
    for a in asset_summary.values():
        a['total_amount'] = str(a['total_amount'])

    # Year-over-year comparison
    yoy_comparison = _build_yoy_comparison(
        period_type, year, quarter, month, entity_ids, asset_ids,
        entity_summary, asset_summary, total,
    )

    # Retained earnings / cumulative rollforward
    retained_earnings = _build_retained_earnings(year, entity_ids, asset_ids)

    return {
        'period': {
            'type': period_type,
            'year': year,
            'quarter': quarter,
            'month': month,
        },
        'summary': {
            'total_distributions': str(total),
            'distribution_count': len(detail),
            'entity_count': len(entity_summary),
            'asset_count': len(asset_summary),
        },
        'by_entity': list(entity_summary.values()),
        'by_asset': list(asset_summary.values()),
        'detail': detail,
        'budget_comparison': _build_budget_comparison(
            period_type, year, quarter, month, entity_ids, asset_ids,
            entity_summary, asset_summary,
        ),
        'yoy_comparison': yoy_comparison,
        'retained_earnings': retained_earnings,
    }


def _build_budget_comparison(
    period_type, year, quarter, month,
    entity_ids, asset_ids,
    entity_summary, asset_summary,
):
    """Compare actual distributions against a matching budget."""
    budgets = Budget.objects.filter(year=year, period_type=period_type)
    if period_type == 'quarterly' and quarter:
        budgets = budgets.filter(quarter=quarter)
    elif period_type == 'monthly' and month:
        budgets = budgets.filter(month=month)

    budget = budgets.prefetch_related('line_items__asset', 'line_items__entity').first()
    if not budget:
        return None

    line_items = budget.line_items.all()
    if asset_ids:
        line_items = line_items.filter(asset_id__in=asset_ids)
    if entity_ids:
        line_items = line_items.filter(entity_id__in=entity_ids)

    # Budget totals by entity and by asset
    budget_by_entity = {}
    budget_by_asset = {}
    total_budgeted = Decimal('0.00')

    for item in line_items:
        total_budgeted += item.amount
        if item.entity_id:
            eid = item.entity_id
            if eid not in budget_by_entity:
                budget_by_entity[eid] = {
                    'entity_id': eid,
                    'entity_name': item.entity.name,
                    'budgeted': Decimal('0.00'),
                }
            budget_by_entity[eid]['budgeted'] += item.amount
        aid = item.asset_id
        if aid not in budget_by_asset:
            budget_by_asset[aid] = {
                'asset_id': aid,
                'asset_name': item.asset.name,
                'budgeted': Decimal('0.00'),
            }
        budget_by_asset[aid]['budgeted'] += item.amount

    # Build entity comparison
    entity_comparison = []
    all_entity_ids = set(budget_by_entity.keys()) | set(entity_summary.keys())
    for eid in all_entity_ids:
        budgeted = budget_by_entity.get(eid, {}).get('budgeted', Decimal('0.00'))
        actual_data = entity_summary.get(eid, {})
        actual = Decimal(actual_data.get('total_amount', '0.00'))
        name = budget_by_entity.get(eid, {}).get('entity_name') or actual_data.get('entity_name', '')
        variance = actual - budgeted
        pct = (variance / budgeted * 100) if budgeted else None
        entity_comparison.append({
            'entity_id': eid,
            'entity_name': name,
            'budgeted': str(budgeted),
            'actual': str(actual),
            'variance': str(variance),
            'variance_pct': str(pct.quantize(Decimal('0.01'))) if pct is not None else None,
        })

    # Build asset comparison
    asset_comparison = []
    all_asset_ids = set(budget_by_asset.keys()) | set(asset_summary.keys())
    for aid in all_asset_ids:
        budgeted = budget_by_asset.get(aid, {}).get('budgeted', Decimal('0.00'))
        actual_data = asset_summary.get(aid, {})
        actual = Decimal(actual_data.get('total_amount', '0.00'))
        name = budget_by_asset.get(aid, {}).get('asset_name') or actual_data.get('asset_name', '')
        variance = actual - budgeted
        pct = (variance / budgeted * 100) if budgeted else None
        asset_comparison.append({
            'asset_id': aid,
            'asset_name': name,
            'budgeted': str(budgeted),
            'actual': str(actual),
            'variance': str(variance),
            'variance_pct': str(pct.quantize(Decimal('0.01'))) if pct is not None else None,
        })

    total_actual = sum(Decimal(e.get('total_amount', '0.00')) for e in entity_summary.values())
    total_variance = total_actual - total_budgeted

    return {
        'budget_id': budget.id,
        'budget_name': budget.name,
        'total_budgeted': str(total_budgeted),
        'total_actual': str(total_actual),
        'total_variance': str(total_variance),
        'total_variance_pct': str(
            (total_variance / total_budgeted * 100).quantize(Decimal('0.01'))
        ) if total_budgeted else None,
        'by_entity': entity_comparison,
        'by_asset': asset_comparison,
    }


def _get_period_allocations(period_type, year, quarter, month, entity_ids, asset_ids):
    """Return filtered allocations for a specific period."""
    distributions = Distribution.objects.filter(distribution_date__year=year)
    if period_type == 'quarterly' and quarter:
        quarter_months = {1: [1,2,3], 2: [4,5,6], 3: [7,8,9], 4: [10,11,12]}
        months = quarter_months.get(quarter, [])
        distributions = distributions.filter(distribution_date__month__in=months)
    elif period_type == 'monthly' and month:
        distributions = distributions.filter(distribution_date__month=month)
    if asset_ids:
        distributions = distributions.filter(asset_id__in=asset_ids)

    allocations = DistributionAllocation.objects.filter(
        distribution__in=distributions
    ).select_related('entity', 'distribution__asset')
    if entity_ids:
        allocations = allocations.filter(entity_id__in=entity_ids)
    return allocations


def _build_yoy_comparison(
    period_type, year, quarter, month,
    entity_ids, asset_ids,
    current_entity_summary, current_asset_summary, current_total,
):
    """Compare current period against the same period in the prior year."""
    prior_year = year - 1
    prior_allocs = _get_period_allocations(
        period_type, prior_year, quarter, month, entity_ids, asset_ids,
    )

    # Aggregate prior-year by entity
    prior_entity = {}
    for alloc in prior_allocs:
        eid = alloc.entity_id
        if eid not in prior_entity:
            prior_entity[eid] = {
                'entity_id': eid,
                'entity_name': alloc.entity.name,
                'total_amount': Decimal('0.00'),
            }
        prior_entity[eid]['total_amount'] += alloc.amount

    # Aggregate prior-year by asset
    prior_asset = {}
    for alloc in prior_allocs:
        aid = alloc.distribution.asset_id
        if aid not in prior_asset:
            prior_asset[aid] = {
                'asset_id': aid,
                'asset_name': alloc.distribution.asset.name,
                'total_amount': Decimal('0.00'),
            }
        prior_asset[aid]['total_amount'] += alloc.amount

    prior_total = sum(e['total_amount'] for e in prior_entity.values())

    def _pct_change(current, prior):
        if prior and prior != 0:
            return str(((current - prior) / abs(prior) * 100).quantize(Decimal('0.01')))
        return None

    # Entity comparison
    all_entity_ids = set(current_entity_summary.keys()) | set(prior_entity.keys())
    entity_yoy = []
    for eid in all_entity_ids:
        cur_data = current_entity_summary.get(eid, {})
        cur_amt = Decimal(cur_data.get('total_amount', '0.00'))
        prior_data = prior_entity.get(eid, {})
        prior_amt = prior_data.get('total_amount', Decimal('0.00'))
        name = cur_data.get('entity_name') or prior_data.get('entity_name', '')
        entity_yoy.append({
            'entity_id': eid,
            'entity_name': name,
            'current_amount': str(cur_amt),
            'prior_amount': str(prior_amt),
            'change': str(cur_amt - prior_amt),
            'change_pct': _pct_change(cur_amt, prior_amt),
        })

    # Asset comparison
    all_asset_ids = set(current_asset_summary.keys()) | set(prior_asset.keys())
    asset_yoy = []
    for aid in all_asset_ids:
        cur_data = current_asset_summary.get(aid, {})
        cur_amt = Decimal(cur_data.get('total_amount', '0.00'))
        prior_data = prior_asset.get(aid, {})
        prior_amt = prior_data.get('total_amount', Decimal('0.00'))
        name = cur_data.get('asset_name') or prior_data.get('asset_name', '')
        asset_yoy.append({
            'asset_id': aid,
            'asset_name': name,
            'current_amount': str(cur_amt),
            'prior_amount': str(prior_amt),
            'change': str(cur_amt - prior_amt),
            'change_pct': _pct_change(cur_amt, prior_amt),
        })

    return {
        'prior_year': prior_year,
        'current_year': year,
        'total_current': str(current_total),
        'total_prior': str(prior_total),
        'total_change': str(current_total - prior_total),
        'total_change_pct': _pct_change(current_total, prior_total),
        'by_entity': entity_yoy,
        'by_asset': asset_yoy,
    }


def _build_retained_earnings(year, entity_ids, asset_ids):
    """
    Build a retained-earnings rollforward per entity.
    Beginning balance (all distributions before this year)
    + Current year distributions
    = Ending balance
    """
    # All allocations before this year
    prior_allocs_qs = DistributionAllocation.objects.filter(
        distribution__distribution_date__year__lt=year,
    ).select_related('entity')
    if asset_ids:
        prior_allocs_qs = prior_allocs_qs.filter(distribution__asset_id__in=asset_ids)
    if entity_ids:
        prior_allocs_qs = prior_allocs_qs.filter(entity_id__in=entity_ids)

    prior_by_entity = {}
    for alloc in prior_allocs_qs:
        eid = alloc.entity_id
        if eid not in prior_by_entity:
            prior_by_entity[eid] = {
                'entity_id': eid,
                'entity_name': alloc.entity.name,
                'beginning_balance': Decimal('0.00'),
            }
        prior_by_entity[eid]['beginning_balance'] += alloc.amount

    # Current year allocations
    current_allocs_qs = DistributionAllocation.objects.filter(
        distribution__distribution_date__year=year,
    ).select_related('entity')
    if asset_ids:
        current_allocs_qs = current_allocs_qs.filter(distribution__asset_id__in=asset_ids)
    if entity_ids:
        current_allocs_qs = current_allocs_qs.filter(entity_id__in=entity_ids)

    current_by_entity = {}
    for alloc in current_allocs_qs:
        eid = alloc.entity_id
        if eid not in current_by_entity:
            current_by_entity[eid] = {
                'entity_id': eid,
                'entity_name': alloc.entity.name,
                'current_year': Decimal('0.00'),
            }
        current_by_entity[eid]['current_year'] += alloc.amount

    # Merge
    all_entity_ids = set(prior_by_entity.keys()) | set(current_by_entity.keys())
    rows = []
    total_beginning = Decimal('0.00')
    total_current = Decimal('0.00')

    for eid in all_entity_ids:
        prior_data = prior_by_entity.get(eid, {})
        current_data = current_by_entity.get(eid, {})
        beginning = prior_data.get('beginning_balance', Decimal('0.00'))
        current = current_data.get('current_year', Decimal('0.00'))
        ending = beginning + current
        name = prior_data.get('entity_name') or current_data.get('entity_name', '')
        total_beginning += beginning
        total_current += current
        rows.append({
            'entity_id': eid,
            'entity_name': name,
            'beginning_balance': str(beginning),
            'current_year_distributions': str(current),
            'ending_balance': str(ending),
        })

    rows.sort(key=lambda r: -float(r['ending_balance']))

    return {
        'year': year,
        'total_beginning_balance': str(total_beginning),
        'total_current_year': str(total_current),
        'total_ending_balance': str(total_beginning + total_current),
        'by_entity': rows,
    }


def generate_dashboard_summary():
    """Quick KPI summary for the dashboard."""
    today = date.today()
    year = today.year

    ytd_dists = Distribution.objects.filter(distribution_date__year=year)
    ytd_allocs = DistributionAllocation.objects.filter(
        distribution__distribution_date__year=year
    ).select_related('entity', 'distribution__asset')

    total_ytd = ytd_allocs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    dist_count = ytd_dists.count()
    avg_distribution = ytd_dists.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0.00')

    # Top entity by total received
    entity_totals = {}
    asset_totals = {}
    for alloc in ytd_allocs:
        eid = alloc.entity_id
        if eid not in entity_totals:
            entity_totals[eid] = {'name': alloc.entity.name, 'total': Decimal('0.00')}
        entity_totals[eid]['total'] += alloc.amount

        aid = alloc.distribution.asset_id
        if aid not in asset_totals:
            asset_totals[aid] = {'name': alloc.distribution.asset.name, 'total': Decimal('0.00')}
        asset_totals[aid]['total'] += alloc.amount

    top_entity = max(entity_totals.values(), key=lambda x: x['total']) if entity_totals else None
    top_asset = max(asset_totals.values(), key=lambda x: x['total']) if asset_totals else None

    # Prior year comparison
    prior_total = DistributionAllocation.objects.filter(
        distribution__distribution_date__year=year - 1
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    yoy_change = total_ytd - prior_total
    yoy_pct = ((yoy_change / abs(prior_total)) * 100).quantize(Decimal('0.01')) if prior_total else None

    # Monthly breakdown for sparkline — single aggregation then fill missing months in Python
    monthly_totals_qs = (
        DistributionAllocation.objects
        .filter(distribution__distribution_date__year=year)
        .values('distribution__distribution_date__month')
        .annotate(total=Sum('amount'))
    )
    monthly_totals_map = {
        entry['distribution__distribution_date__month']: entry['total'] or Decimal('0.00')
        for entry in monthly_totals_qs
    }

    monthly = []
    for m in range(1, 13):
        month_total = monthly_totals_map.get(m, Decimal('0.00'))
        monthly.append({'month': m, 'amount': str(month_total)})

    return {
        'year': year,
        'total_ytd': str(total_ytd),
        'distribution_count': dist_count,
        'avg_distribution': str(avg_distribution.quantize(Decimal('0.01'))),
        'entity_count': Entity.objects.count(),
        'asset_count': Asset.objects.count(),
        'top_entity': {'name': top_entity['name'], 'total': str(top_entity['total'])} if top_entity else None,
        'top_asset': {'name': top_asset['name'], 'total': str(top_asset['total'])} if top_asset else None,
        'prior_year_total': str(prior_total),
        'yoy_change': str(yoy_change),
        'yoy_change_pct': str(yoy_pct) if yoy_pct is not None else None,
        'monthly': monthly,
    }


def generate_portfolio_by_class(entity_ids=None, tag_slugs=None):
    """
    Portfolio-by-class report showing allocation breakdown by asset type.
    Optionally filtered by entity and/or tag.
    """
    assets = Asset.objects.prefetch_related('tags', 'fmv_snapshots', 'ownerships').all()

    # Tag filtering
    if tag_slugs:
        for slug in tag_slugs:
            assets = assets.filter(tags__slug=slug)
        assets = assets.distinct()

    # Build per-asset data with latest FMV
    asset_data = []
    for asset in assets:
        latest = asset.fmv_snapshots.order_by('-snapshot_date').first()
        if not latest:
            continue

        fmv = latest.value

        # If entity filter, scale by ownership percentage
        if entity_ids:
            ownerships = EntityAssetOwnership.objects.filter(
                asset=asset, entity_id__in=entity_ids
            )
            if not ownerships.exists():
                continue
            pct = sum(o.percentage for o in ownerships)
            fmv = fmv * pct / 100

        asset_data.append({
            'asset_id': asset.id,
            'asset_name': asset.name,
            'asset_type': asset.asset_type,
            'fmv': fmv,
            'tags': [t.slug for t in asset.tags.all()],
        })

    # Group by asset type
    by_type = {}
    total_fmv = Decimal('0.00')
    for a in asset_data:
        t = a['asset_type']
        if t not in by_type:
            by_type[t] = {
                'asset_type': t,
                'total_fmv': Decimal('0.00'),
                'asset_count': 0,
                'assets': [],
            }
        by_type[t]['total_fmv'] += a['fmv']
        by_type[t]['asset_count'] += 1
        by_type[t]['assets'].append({
            'asset_id': a['asset_id'],
            'asset_name': a['asset_name'],
            'fmv': str(a['fmv']),
        })
        total_fmv += a['fmv']

    # Add allocation percentage
    for group in by_type.values():
        pct = (group['total_fmv'] / total_fmv * 100) if total_fmv > 0 else Decimal('0')
        group['allocation_pct'] = str(pct.quantize(Decimal('0.01')))
        group['total_fmv'] = str(group['total_fmv'])

    result = sorted(by_type.values(), key=lambda x: -float(x['total_fmv']))

    return {
        'total_fmv': str(total_fmv),
        'by_asset_type': result,
        'filters': {
            'entity_ids': entity_ids,
            'tag_slugs': tag_slugs,
        },
    }


def generate_net_worth_summary():
    """
    Net worth summary per entity (principal) and consolidated.
    Uses latest FMV snapshots scaled by ownership percentages.
    """
    entities = Entity.objects.all()
    result = []
    consolidated = Decimal('0.00')

    for entity in entities:
        ownerships = EntityAssetOwnership.objects.filter(
            entity=entity
        ).select_related('asset')

        entity_total = Decimal('0.00')
        holdings = []

        for ownership in ownerships:
            latest = FMVSnapshot.objects.filter(
                asset=ownership.asset
            ).order_by('-snapshot_date').first()

            if latest:
                share = latest.value * ownership.percentage / 100
                entity_total += share
                holdings.append({
                    'asset_id': ownership.asset.id,
                    'asset_name': ownership.asset.name,
                    'asset_type': ownership.asset.asset_type,
                    'total_fmv': str(latest.value),
                    'ownership_pct': str(ownership.percentage),
                    'entity_share': str(share.quantize(Decimal('0.01'))),
                })

        consolidated += entity_total
        result.append({
            'entity_id': entity.id,
            'entity_name': entity.name,
            'entity_type': entity.entity_type,
            'net_worth': str(entity_total.quantize(Decimal('0.01'))),
            'holdings_count': len(holdings),
            'holdings': holdings,
        })

    result.sort(key=lambda x: -float(x['net_worth']))

    return {
        'consolidated_net_worth': str(consolidated.quantize(Decimal('0.01'))),
        'by_entity': result,
    }
