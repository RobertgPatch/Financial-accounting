"""Auto-populate portfolio data from confirmed K-1 documents.

Creates Distribution and DistributionAllocation records from K-1 line 19
(actual cash/property distributions) only, and creates/updates Activity ledger
records that capture all income line items (interest, dividends, capital gains,
ordinary income, etc.).
"""
import logging
from datetime import date
from decimal import Decimal

from django.db import transaction

from .models import (
    K1Document, Distribution, DistributionAllocation, EntityAssetOwnership,
    Activity,
)

logger = logging.getLogger(__name__)

# Only K-1 line 19 represents actual cash/property distributions to the partner.
# All other income lines (1, 5, 6a, 8, 9a, etc.) are income allocations that
# belong in the Activity ledger, not in the Distributions table.
DISTRIBUTION_LINE_NUMBERS = {'19'}

# Map K-1 line 19 codes to distribution types
LINE_19_CODE_TO_DIST_TYPE = {
    'A': 'regular',   # Cash and marketable securities
    'B': 'regular',   # Distribution subject to section 737
    'C': 'regular',   # Other property
}

# Map K-1 line numbers to Activity income columns
LINE_TO_INCOME_FIELD = {
    '5': 'interest',
    '6a': 'dividends',
    '6b': 'dividends',
    '8': 'capital_gains',
    '9a': 'capital_gains',
    '9b': 'capital_gains',
    '9c': 'capital_gains',
    '10': 'capital_gains',
}


def populate_portfolio_from_k1(k1_document):
    """Create Distribution records and an Activity record from a confirmed K-1.

    Only K-1 line 19 items (actual partner distributions) produce Distribution
    rows.  All other income line items (ordinary income, interest, dividends,
    capital gains, etc.) are accumulated exclusively into the Activity ledger so
    that the Distributions table accurately reflects cash-flow events.

    Args:
        k1_document: A K1Document instance with status='confirmed'.

    Returns:
        dict with keys:
            distributions_created (int): number of Distribution rows created.
            total_distributions (Decimal): sum of line-19 distribution amounts.
            income_items_processed (int): number of non-distribution income lines
                captured in the Activity ledger.
            details (list): per-distribution detail dicts.
            activity_id (int|None): PK of the created/updated Activity record.

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
        'total_distributions': Decimal('0.00'),
        'income_items_processed': 0,
        'details': [],
        'activity_id': None,
    }

    # Use Dec 31 of the tax year as the distribution date
    dist_date = date(k1_document.tax_year, 12, 31)

    # Accumulators for Activity record
    act_interest = Decimal('0.00')
    act_dividends = Decimal('0.00')
    act_capital_gains = Decimal('0.00')
    act_remaining = Decimal('0.00')
    act_distributions = Decimal('0.00')
    act_contributions = Decimal('0.00')

    with transaction.atomic():
        for item in items:
            amount = item.amount or Decimal('0.00')
            code_label = f" ({item.code})" if item.code else ""
            description = item.description or f"Line {item.line_number}{code_label}"

            # ------------------------------------------------------------------
            # Create Distribution rows ONLY for line 19 (actual distributions).
            # Income allocation lines (ordinary income, interest, gains, etc.)
            # must NOT produce Distribution rows — they go to the Activity ledger
            # only, which avoids inflating the Distributions table with non-cash
            # income items.
            # ------------------------------------------------------------------
            if item.line_number in DISTRIBUTION_LINE_NUMBERS:
                dist_type = LINE_19_CODE_TO_DIST_TYPE.get(item.code or '', 'regular')

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
                        pct = ownerships[0].percentage or Decimal('100.0000')

                    DistributionAllocation.objects.create(
                        distribution=dist,
                        entity=entity,
                        amount=item.amount,
                        percentage=pct,
                        notes=f"K-1 Line {item.line_number}{code_label}",
                    )

                results['distributions_created'] += 1
                results['total_distributions'] += item.amount
                results['details'].append({
                    'line_number': item.line_number,
                    'code': item.code,
                    'amount': str(item.amount),
                    'distribution_id': dist.id,
                    'description': description,
                })
            else:
                results['income_items_processed'] += 1

            # ------------------------------------------------------------------
            # Accumulate every item into the appropriate Activity ledger bucket.
            # Line 19 → act_distributions; other lines → income-type buckets.
            # ------------------------------------------------------------------
            income_field = LINE_TO_INCOME_FIELD.get(item.line_number)
            if item.line_number in DISTRIBUTION_LINE_NUMBERS:
                act_distributions += amount
            elif income_field == 'interest':
                act_interest += amount
            elif income_field == 'dividends':
                act_dividends += amount
            elif income_field == 'capital_gains':
                act_capital_gains += amount
            else:
                act_remaining += amount

        # Build Activity record from K-1 data
        if entity:
            cap = getattr(k1_document, 'capital_account', None)

            # Capital contributed from capital account section
            if cap and cap.capital_contributed:
                act_contributions = cap.capital_contributed

            # Ending K-1 capital from capital account section
            ending_k1_cap = Decimal('0.00')
            if cap:
                ending_k1_cap = cap.ending_balance or Decimal('0.00')

            # Withdrawals from capital account as distributions, unless we already have line 19
            if cap and cap.withdrawals and act_distributions == 0:
                act_distributions = abs(cap.withdrawals)

            # Other adjustments from capital account
            other_adj = Decimal('0.00')
            if cap and cap.other_increase_decrease:
                other_adj = cap.other_increase_decrease

            # Activity.save() auto-computes: beginning_basis, total_income,
            # ending_tax_basis, book_to_tax_adj, k1_capital_vs_tax_diff,
            # excess_distribution, negative_basis, basis_change
            activity, _created = Activity.objects.update_or_create(
                year=k1_document.tax_year,
                entity=entity,
                asset=k1_document.asset,
                defaults={
                    'contributions': act_contributions,
                    'interest': act_interest,
                    'dividends': act_dividends,
                    'capital_gains': act_capital_gains,
                    'remaining_k1_income': act_remaining,
                    'distributions': act_distributions,
                    'other_adjustments': other_adj,
                    'ending_k1_capital': ending_k1_cap,
                    'source_k1_document': k1_document,
                    'notes': f"Auto-populated from K-1 {k1_document.tax_year}",
                },
            )
            results['activity_id'] = activity.id

    logger.info(
        f"Populated {results['distributions_created']} distributions "
        f"(${results['total_distributions']}) and "
        f"{results['income_items_processed']} income items into Activity ledger "
        f"from K-1 document {k1_document.id}"
    )

    return results
