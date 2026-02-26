from decimal import Decimal
from datetime import date
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
