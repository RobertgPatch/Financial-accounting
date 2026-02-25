from decimal import Decimal
from datetime import date
from .models import Distribution, DistributionAllocation, Entity, Asset, EntityAssetOwnership


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

    # Aggregate by asset
    asset_summary = {}
    for dist in distributions:
        aid = dist.asset_id
        if aid not in asset_summary:
            asset_summary[aid] = {
                'asset_id': aid,
                'asset_name': dist.asset.name,
                'asset_type': dist.asset.asset_type,
                'total_amount': Decimal('0.00'),
                'distribution_count': 0,
            }
        asset_summary[aid]['total_amount'] += dist.total_amount
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
            'entity_count': len(entity_summary),
            'asset_count': len(asset_summary),
        },
        'by_entity': list(entity_summary.values()),
        'by_asset': list(asset_summary.values()),
        'detail': detail,
    }
