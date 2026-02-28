from decimal import Decimal
from datetime import date
from django.db.models import Sum, Count, Avg, F, Q
from .models import Distribution, DistributionAllocation, Entity, Asset, EntityAssetOwnership, Budget, BudgetLineItem


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

    # Monthly breakdown for sparkline
    monthly = []
    for m in range(1, 13):
        month_total = DistributionAllocation.objects.filter(
            distribution__distribution_date__year=year,
            distribution__distribution_date__month=m,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
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
