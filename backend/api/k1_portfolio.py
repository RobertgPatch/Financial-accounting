"""Auto-populate portfolio data from confirmed K-1 documents.

Creates Distribution and DistributionAllocation records from K-1 income items.
"""
import logging
from datetime import date
from decimal import Decimal

from django.db import transaction

from .models import (
    K1Document, Distribution, DistributionAllocation, EntityAssetOwnership,
)

logger = logging.getLogger(__name__)

# Map K-1 line numbers to distribution types
LINE_TO_DIST_TYPE = {
    '1': 'regular',        # Ordinary business income
    '2': 'regular',        # Net rental real estate
    '3': 'regular',        # Other net rental
    '4a': 'regular',       # Guaranteed payments for services
    '4b': 'regular',       # Guaranteed payments for capital
    '4c': 'regular',       # Total guaranteed payments
    '5': 'regular',        # Interest income
    '6a': 'regular',       # Ordinary dividends
    '6b': 'regular',       # Qualified dividends
    '7': 'regular',        # Royalties
    '8': 'regular',        # Net short-term capital gain
    '9a': 'regular',       # Net long-term capital gain
    '9b': 'regular',       # Collectibles gain
    '9c': 'regular',       # Unrecaptured section 1250
    '10': 'regular',       # Net section 1231 gain
    '19': 'regular',       # Distributions (main line)
}


def populate_portfolio_from_k1(k1_document):
    """Create Distribution records from a confirmed K-1 document.

    Args:
        k1_document: A K1Document instance with status='confirmed'.

    Returns:
        dict with keys: distributions_created (int), total_amount (Decimal),
        details (list of dicts with line_number, amount, distribution_id).

    Raises:
        ValueError: If document is not confirmed or already populated.
    """
    if k1_document.status != 'confirmed':
        raise ValueError('K-1 document must be confirmed before populating portfolio.')

    # Duplicate detection: check if distributions already exist for this K-1
    existing = Distribution.objects.filter(source_k1_document=k1_document).count()
    if existing > 0:
        raise ValueError(
            f'Portfolio already populated from this K-1 document '
            f'({existing} distribution(s) exist). Delete them first to re-populate.'
        )

    if not k1_document.asset:
        raise ValueError(
            'K-1 document must be linked to an asset before populating portfolio. '
            'Please set the asset on the review page.'
        )

    # Gather income items with actual amounts (skip supplementals without amounts)
    items = k1_document.income_items.exclude(amount__isnull=True).order_by('line_number', 'code')
    if not items.exists():
        raise ValueError('No income items with amounts found to populate.')

    # Get entity-level ownership for allocations
    entity = k1_document.entity
    ownerships = []
    if entity:
        ownerships = list(
            EntityAssetOwnership.objects.filter(
                asset=k1_document.asset,
                entity=entity,
            )
        )

    results = {
        'distributions_created': 0,
        'total_amount': Decimal('0.00'),
        'details': [],
    }

    # Use Dec 31 of the tax year as the distribution date
    dist_date = date(k1_document.tax_year, 12, 31)

    with transaction.atomic():
        for item in items:
            dist_type = LINE_TO_DIST_TYPE.get(item.line_number, 'regular')
            code_label = f" ({item.code})" if item.code else ""
            description = item.description or f"Line {item.line_number}{code_label}"

            dist = Distribution.objects.create(
                asset=k1_document.asset,
                distribution_date=dist_date,
                total_amount=item.amount,
                distribution_type=dist_type,
                notes=f"Auto-populated from K-1 {k1_document.tax_year}: {description}",
                source_k1_document=k1_document,
            )

            # Create allocation if entity is linked
            if entity:
                pct = Decimal('100.0000')
                if ownerships:
                    pct = ownerships[0].ownership_percentage or Decimal('100.0000')

                DistributionAllocation.objects.create(
                    distribution=dist,
                    entity=entity,
                    amount=item.amount,
                    percentage=pct,
                    notes=f"K-1 Line {item.line_number}{code_label}",
                )

            results['distributions_created'] += 1
            results['total_amount'] += item.amount
            results['details'].append({
                'line_number': item.line_number,
                'code': item.code,
                'amount': str(item.amount),
                'distribution_id': dist.id,
                'description': description,
            })

    logger.info(
        f"Populated {results['distributions_created']} distributions "
        f"(${results['total_amount']}) from K-1 document {k1_document.id}"
    )

    return results
