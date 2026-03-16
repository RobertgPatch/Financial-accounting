"""Generate realistic mock K-1 data and run the full populate pipeline.

This replaces PDF upload for dev/demo purposes.  For each entity/asset
ownership pair it creates:

  K1Document  →  K1PartnershipInfo
                  K1PartnerInfo
                  K1IncomeItem[]   (realistic amounts per asset type)
                  K1CapitalAccount

Then confirms & populates → Distribution + Activity records appear.
"""

import logging
import random
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .models import (
    Entity, Asset, EntityAssetOwnership,
    K1Document, K1PartnershipInfo, K1PartnerInfo,
    K1IncomeItem, K1CapitalAccount,
    Distribution,
)
from .k1_portfolio import populate_portfolio_from_k1

logger = logging.getLogger(__name__)

# ── Income profiles by asset type ──────────────────────────────────────
# Each key maps to a list of (line_number, description, min, max) tuples.
# Amounts are in USD and represent the partner's share (already %).

PROFILES = {
    'private_equity': [
        ('1',  'Ordinary business income (loss)',   -50_000,  200_000),
        ('8',  'Net short-term capital gain (loss)', -20_000,   80_000),
        ('9a', 'Net long-term capital gain (loss)',   50_000,  600_000),
        ('10', 'Net section 1231 gain (loss)',            0,  150_000),
        ('5',  'Interest income',                     1_000,   25_000),
        ('19', 'Distributions',                      50_000,  400_000),
    ],
    'venture_capital': [
        ('1',  'Ordinary business income (loss)',  -100_000,   50_000),
        ('9a', 'Net long-term capital gain (loss)',  20_000,  800_000),
        ('5',  'Interest income',                       500,   10_000),
        ('19', 'Distributions',                      10_000,  300_000),
    ],
    'real_estate': [
        ('1',  'Ordinary business income (loss)',    10_000,  300_000),
        ('2',  'Net rental real estate income',      20_000,  500_000),
        ('5',  'Interest income',                     2_000,   40_000),
        ('6a', 'Ordinary dividends',                  5_000,   60_000),
        ('19', 'Distributions',                      80_000,  500_000),
    ],
    'credit': [
        ('1',  'Ordinary business income (loss)',   -10_000,   80_000),
        ('5',  'Interest income',                    50_000,  350_000),
        ('8',  'Net short-term capital gain (loss)', -30_000,   60_000),
        ('9a', 'Net long-term capital gain (loss)',  -20_000,  100_000),
        ('19', 'Distributions',                      60_000,  400_000),
    ],
    'infrastructure': [
        ('1',  'Ordinary business income (loss)',    30_000,  200_000),
        ('5',  'Interest income',                    10_000,   80_000),
        ('6a', 'Ordinary dividends',                 20_000,  120_000),
        ('6b', 'Qualified dividends',                10_000,   60_000),
        ('19', 'Distributions',                      50_000,  300_000),
    ],
}

# Fallback for any other asset type
PROFILES['default'] = [
    ('1',  'Ordinary business income (loss)',   -30_000,  150_000),
    ('5',  'Interest income',                     2_000,   40_000),
    ('9a', 'Net long-term capital gain (loss)',   10_000,  200_000),
    ('19', 'Distributions',                       20_000,  200_000),
]

# Fake EINs / TINs
def _fake_ein():
    return f"{random.randint(80, 89)}-{random.randint(1000000, 9999999)}"


def _fake_tin():
    return f"***-**-{random.randint(1000, 9999)}"


def _rand_amount(lo, hi):
    """Return a Decimal rounded to cents, uniformly sampled in [lo, hi]."""
    return Decimal(str(round(random.uniform(lo, hi), 2)))


def simulate_k1_for_pair(entity, asset, ownership, year):
    """Create a full mock K-1 document for one entity-asset pair.

    Returns dict with k1_document, populate_result.
    """
    profile = PROFILES.get(asset.asset_type, PROFILES['default'])

    # ── K1Document ─────────────────────────────────────────────────
    # Create a tiny dummy PDF file (1-byte placeholder)
    dummy_content = ContentFile(b'%PDF-1.4 simulated', name=f'simulated_{asset.name}_{year}.pdf')

    k1_doc = K1Document(
        entity=entity,
        asset=asset,
        tax_year=year,
        status='draft',
        asset_type_classification=asset.asset_type,
        is_final=True,
        is_amended=False,
        original_filename=f'Simulated K-1 — {asset.name} ({year}).pdf',
        extraction_method='text',
        notes=f'Simulated K-1 for {entity.name} / {asset.name} ({year})',
    )
    k1_doc.document = dummy_content
    k1_doc.save()

    # ── Partnership Info ───────────────────────────────────────────
    K1PartnershipInfo.objects.create(
        document=k1_doc,
        ein=_fake_ein(),
        name=asset.name,
        address=f'{random.randint(100, 9999)} Fund Ave',
        city=random.choice(['New York', 'San Francisco', 'Chicago', 'Dallas', 'Miami']),
        state=random.choice(['NY', 'CA', 'IL', 'TX', 'FL']),
        zip_code=f'{random.randint(10000, 99999)}',
        irs_center='Ogden',
        is_ptp=False,
    )

    # ── Partner Info ───────────────────────────────────────────────
    pct = float(ownership.percentage)
    K1PartnerInfo.objects.create(
        document=k1_doc,
        tin=_fake_tin(),
        name=entity.name,
        address='123 Family Office Blvd',
        city='Greenwich',
        state='CT',
        zip_code='06830',
        is_general_partner=False,
        is_domestic=True,
        entity_type=entity.entity_type,
        profit_beginning_pct=Decimal(str(pct)),
        profit_ending_pct=Decimal(str(pct)),
        loss_beginning_pct=Decimal(str(pct)),
        loss_ending_pct=Decimal(str(pct)),
        capital_beginning_pct=Decimal(str(pct)),
        capital_ending_pct=Decimal(str(pct)),
    )

    # ── Income Items ───────────────────────────────────────────────
    income_total = Decimal('0.00')
    dist_amount = Decimal('0.00')
    contrib_amount = Decimal('0.00')

    for line_no, description, lo, hi in profile:
        amount = _rand_amount(lo, hi)
        K1IncomeItem.objects.create(
            document=k1_doc,
            line_number=line_no,
            description=description,
            amount=amount,
        )
        if line_no == '19':
            dist_amount = amount
        else:
            income_total += amount

    # ── Capital Account ────────────────────────────────────────────
    # Simulate realistic beginning → ending flow
    beginning = _rand_amount(100_000, 2_000_000)
    contributed = _rand_amount(0, 100_000) if random.random() < 0.3 else Decimal('0.00')
    contrib_amount = contributed
    withdrawals = dist_amount  # withdrawals ≈ distributions
    other_adj = _rand_amount(-20_000, 20_000) if random.random() < 0.25 else Decimal('0.00')
    ending = beginning + contributed + income_total - withdrawals + other_adj

    K1CapitalAccount.objects.create(
        document=k1_doc,
        beginning_balance=beginning,
        capital_contributed=contributed,
        net_income=income_total,
        other_increase_decrease=other_adj,
        withdrawals=withdrawals,
        ending_balance=ending,
        tax_basis_method='Tax',
    )

    # ── Confirm ────────────────────────────────────────────────────
    k1_doc.status = 'confirmed'
    k1_doc.confirmed_at = timezone.now()
    k1_doc.save(update_fields=['status', 'confirmed_at'])

    # ── Populate ───────────────────────────────────────────────────
    result = populate_portfolio_from_k1(k1_doc)

    return {
        'k1_document_id': k1_doc.id,
        'entity': entity.name,
        'asset': asset.name,
        'year': year,
        'distributions_created': result['distributions_created'],
        'total_distributions': str(result['total_distributions']),
        'income_items_processed': result['income_items_processed'],
        'activity_id': result.get('activity_id'),
    }


def simulate_k1_batch(year, entity_id=None, asset_id=None):
    """Simulate K-1 uploads for all (or filtered) entity-asset ownership pairs.

    For each pair that does NOT already have a confirmed K-1 for that year,
    generates mock data and runs the full pipeline.

    Args:
        year: Tax year (int).
        entity_id: Optional — limit to one entity.
        asset_id: Optional — limit to one asset.

    Returns:
        dict with 'created' list and 'skipped' list.
    """
    qs = EntityAssetOwnership.objects.select_related('entity', 'asset').all()
    if entity_id:
        qs = qs.filter(entity_id=entity_id)
    if asset_id:
        qs = qs.filter(asset_id=asset_id)

    created = []
    skipped = []

    for own in qs:
        # Skip if already has K-1 distributions for this year + entity + asset
        if Distribution.objects.filter(
            source_k1_document__entity=own.entity,
            source_k1_document__asset=own.asset,
            source_k1_document__tax_year=year,
        ).exists():
            skipped.append({
                'entity': own.entity.name,
                'asset': own.asset.name,
                'reason': 'K-1 already populated for this year',
            })
            continue

        with transaction.atomic():
            info = simulate_k1_for_pair(own.entity, own.asset, own, year)
        created.append(info)

    return {'created': created, 'skipped': skipped}
