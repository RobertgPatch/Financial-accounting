"""
Seed the database with test data that matches the K-1 → Activity data flow.

The K-1 is the source of truth — when it's ingested and confirmed, the user
assigns entity + asset (partnership) + asset type + optional ownership %.
The populate step then creates Distribution / Activity records.

This seeder creates:
  1.  Entities (investors / trusts)
  2.  Assets (partnerships / funds)  — each has an asset_type
  3.  Ownerships (entity ↔ asset with %)
  4.  Commitments + Capital Calls
  5.  FMV Snapshots

It does NOT create K-1 documents, Distributions, or Activity rows.
Those are populated via the "Simulate K-1 Upload" button in the UI,
which generates realistic mock K-1 data and runs the confirm → populate
pipeline.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date


class Command(BaseCommand):
    help = 'Clear all data and seed entities, assets, ownerships, commitments, and FMV snapshots'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-clear', action='store_true',
            help='Skip clearing existing data (append instead)',
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        from api.models import (
            Entity, Asset, EntityAssetOwnership,
            Distribution, DistributionAllocation,
            AssetTag, FMVSnapshot,
            Budget, BudgetLineItem,
            Commitment, CapitalCall,
            K1Document, K1PartnershipInfo, K1PartnerInfo,
            K1IncomeItem, K1CapitalAccount,
            Activity,
        )

        if not kwargs.get('no_clear'):
            self.stdout.write('Clearing all existing data...')
            Activity.objects.all().delete()
            K1CapitalAccount.objects.all().delete()
            K1IncomeItem.objects.all().delete()
            K1PartnerInfo.objects.all().delete()
            K1PartnershipInfo.objects.all().delete()
            K1Document.objects.all().delete()
            CapitalCall.objects.all().delete()
            Commitment.objects.all().delete()
            DistributionAllocation.objects.all().delete()
            Distribution.objects.all().delete()
            BudgetLineItem.objects.all().delete()
            Budget.objects.all().delete()
            FMVSnapshot.objects.all().delete()
            EntityAssetOwnership.objects.all().delete()
            Asset.objects.all().delete()
            Entity.objects.all().delete()
            AssetTag.objects.all().delete()
            try:
                from plaid_integration.models import PlaidAccount, PlaidItem
                PlaidAccount.objects.all().delete()
                PlaidItem.objects.all().delete()
            except Exception:
                pass
            self.stdout.write(self.style.WARNING('  All tables cleared.'))

        self.stdout.write('Creating seed data (Setup sheet only)...')

        # ── Tags ──
        tag_pe = AssetTag.objects.create(name='Private Equity', slug='private-equity', color='#8B5CF6')
        tag_vc = AssetTag.objects.create(name='Venture Capital', slug='venture-capital', color='#3B82F6')
        tag_re = AssetTag.objects.create(name='Real Estate', slug='real-estate', color='#10B981')
        tag_credit = AssetTag.objects.create(name='Credit', slug='credit', color='#EF4444')
        tag_growth = AssetTag.objects.create(name='Growth', slug='growth', color='#F59E0B')
        tag_infra = AssetTag.objects.create(name='Infrastructure', slug='infrastructure', color='#6366F1')

        # ════════════════════════════════════════════════════════════════
        # ENTITIES (the investors)
        # ════════════════════════════════════════════════════════════════
        acme = Entity.objects.create(
            name='Acme Capital Partners',
            entity_type='LLC',
            description='Family office vehicle for domestic PE/VC investments.',
            email='acme@example.com',
        )
        blue = Entity.objects.create(
            name='Blue Harbor Family Trust',
            entity_type='trust',
            description='Irrevocable trust holding diversified alt. investments.',
            email='blue@example.com',
        )
        cypress = Entity.objects.create(
            name='Cypress Growth Holdings',
            entity_type='company',
            description='Growth-oriented holding company.',
            email='cypress@example.com',
        )
        drake = Entity.objects.create(
            name='Drake Equity Group',
            entity_type='partnership',
            description='Multi-strategy partnership winding down legacy funds.',
            email='drake@example.com',
        )

        # ════════════════════════════════════════════════════════════════
        # ASSETS (the partnerships / funds)
        # ════════════════════════════════════════════════════════════════
        alpha = Asset.objects.create(
            name='Alpha Buyout Fund III',
            asset_type='private_equity',
            description='Large-cap buyout fund (vintage 2018). EIN 82-1234567.',
        )
        alpha.tags.add(tag_pe)

        beacon = Asset.objects.create(
            name='Beacon Real Assets II',
            asset_type='real_estate',
            description='Core-plus real estate fund (vintage 2021). EIN 83-2345678.',
        )
        beacon.tags.add(tag_re)

        catalyst = Asset.objects.create(
            name='Catalyst Ventures IV',
            asset_type='venture_capital',
            description='Early-stage venture fund (vintage 2022). EIN 84-3456789.',
        )
        catalyst.tags.add(tag_vc, tag_growth)

        delta = Asset.objects.create(
            name='Delta Credit Opportunities I',
            asset_type='credit',
            description='Distressed / special-situations credit (vintage 2019). EIN 85-4567890.',
        )
        delta.tags.add(tag_credit)

        evergreen = Asset.objects.create(
            name='Evergreen Infrastructure LP',
            asset_type='infrastructure',
            description='Core infra fund — toll roads & utilities (vintage 2020). EIN 86-5678901.',
        )
        evergreen.tags.add(tag_infra)

        frontier = Asset.objects.create(
            name='Frontier Growth Equity V',
            asset_type='private_equity',
            description='Growth equity targeting healthcare & tech (vintage 2023). EIN 87-6789012.',
        )
        frontier.tags.add(tag_pe, tag_growth)

        # ════════════════════════════════════════════════════════════════
        # OWNERSHIPS (entity ↔ asset + % + inception date)
        #   K-1 amounts already reflect the partner's share.
        #   Ownership % is recorded for reference / gross-up calcs only.
        # ════════════════════════════════════════════════════════════════
        ownerships = [
            # Acme owns 3 funds
            (acme, alpha,     Decimal('80.0000'),  date(2018, 4, 1)),
            (acme, catalyst,  Decimal('15.0000'),  date(2022, 3, 1)),
            (acme, frontier,  Decimal('25.0000'),  date(2023, 6, 1)),
            # Blue Harbor owns 2 funds
            (blue, beacon,    Decimal('100.0000'), date(2021, 7, 1)),
            (blue, evergreen, Decimal('50.0000'),  date(2020, 1, 15)),
            # Cypress owns 2 funds
            (cypress, catalyst,  Decimal('10.0000'),  date(2022, 3, 1)),
            (cypress, frontier,  Decimal('12.5000'),  date(2023, 6, 1)),
            # Drake owns 2 funds
            (drake, delta,    Decimal('100.0000'), date(2019, 9, 1)),
            (drake, evergreen, Decimal('50.0000'), date(2020, 1, 15)),
        ]
        for entity, asset, pct, eff_date in ownerships:
            EntityAssetOwnership.objects.create(
                entity=entity, asset=asset,
                percentage=pct, effective_date=eff_date,
            )

        # ════════════════════════════════════════════════════════════════
        # COMMITMENTS + CAPITAL CALLS
        # ════════════════════════════════════════════════════════════════

        # Acme → Alpha ($2M commitment, fully called)
        c = Commitment.objects.create(
            entity=acme, asset=alpha,
            commitment_date=date(2018, 4, 1),
            original_amount=Decimal('2000000.00'),
        )
        for dt, amt in [
            (date(2018, 6, 1), Decimal('600000.00')),
            (date(2019, 1, 1), Decimal('600000.00')),
            (date(2019, 7, 1), Decimal('500000.00')),
            (date(2020, 3, 1), Decimal('300000.00')),
        ]:
            CapitalCall.objects.create(commitment=c, call_date=dt, amount=amt)

        # Acme → Catalyst ($150K)
        c = Commitment.objects.create(
            entity=acme, asset=catalyst,
            commitment_date=date(2022, 3, 1),
            original_amount=Decimal('150000.00'),
        )
        for dt, amt in [
            (date(2022, 6, 1), Decimal('50000.00')),
            (date(2023, 3, 1), Decimal('50000.00')),
            (date(2024, 1, 1), Decimal('30000.00')),
        ]:
            CapitalCall.objects.create(commitment=c, call_date=dt, amount=amt)

        # Acme → Frontier ($500K)
        c = Commitment.objects.create(
            entity=acme, asset=frontier,
            commitment_date=date(2023, 6, 1),
            original_amount=Decimal('500000.00'),
        )
        for dt, amt in [
            (date(2023, 9, 1), Decimal('150000.00')),
            (date(2024, 6, 1), Decimal('150000.00')),
        ]:
            CapitalCall.objects.create(commitment=c, call_date=dt, amount=amt)

        # Blue → Beacon ($3M, 100%)
        c = Commitment.objects.create(
            entity=blue, asset=beacon,
            commitment_date=date(2021, 7, 1),
            original_amount=Decimal('3000000.00'),
        )
        for dt, amt in [
            (date(2021, 9, 1), Decimal('750000.00')),
            (date(2022, 3, 1), Decimal('750000.00')),
            (date(2022, 9, 1), Decimal('750000.00')),
            (date(2023, 6, 1), Decimal('500000.00')),
        ]:
            CapitalCall.objects.create(commitment=c, call_date=dt, amount=amt)

        # Blue → Evergreen ($600K, 50%)
        c = Commitment.objects.create(
            entity=blue, asset=evergreen,
            commitment_date=date(2020, 1, 15),
            original_amount=Decimal('600000.00'),
        )
        for dt, amt in [
            (date(2020, 4, 1), Decimal('200000.00')),
            (date(2021, 1, 1), Decimal('200000.00')),
            (date(2022, 1, 1), Decimal('200000.00')),
        ]:
            CapitalCall.objects.create(commitment=c, call_date=dt, amount=amt)

        # Cypress → Catalyst ($100K, 10%)
        c = Commitment.objects.create(
            entity=cypress, asset=catalyst,
            commitment_date=date(2022, 3, 1),
            original_amount=Decimal('100000.00'),
        )
        for dt, amt in [
            (date(2022, 6, 1), Decimal('35000.00')),
            (date(2023, 3, 1), Decimal('35000.00')),
        ]:
            CapitalCall.objects.create(commitment=c, call_date=dt, amount=amt)

        # Cypress → Frontier ($250K, 12.5%)
        c = Commitment.objects.create(
            entity=cypress, asset=frontier,
            commitment_date=date(2023, 6, 1),
            original_amount=Decimal('250000.00'),
        )
        CapitalCall.objects.create(
            commitment=c, call_date=date(2023, 9, 1), amount=Decimal('75000.00'),
        )

        # Drake → Delta ($2M, 100%)
        c = Commitment.objects.create(
            entity=drake, asset=delta,
            commitment_date=date(2019, 9, 1),
            original_amount=Decimal('2000000.00'),
        )
        for dt, amt in [
            (date(2019, 10, 1), Decimal('700000.00')),
            (date(2020, 4, 1),  Decimal('700000.00')),
            (date(2020, 10, 1), Decimal('600000.00')),
        ]:
            CapitalCall.objects.create(commitment=c, call_date=dt, amount=amt)

        # Drake → Evergreen ($600K, 50%)
        c = Commitment.objects.create(
            entity=drake, asset=evergreen,
            commitment_date=date(2020, 1, 15),
            original_amount=Decimal('600000.00'),
        )
        for dt, amt in [
            (date(2020, 4, 1), Decimal('200000.00')),
            (date(2021, 1, 1), Decimal('200000.00')),
            (date(2022, 1, 1), Decimal('200000.00')),
        ]:
            CapitalCall.objects.create(commitment=c, call_date=dt, amount=amt)

        # ════════════════════════════════════════════════════════════════
        # FMV SNAPSHOTS (year-end NAVs)
        # ════════════════════════════════════════════════════════════════
        fmv_data = [
            (alpha,     date(2024, 12, 31), Decimal('800000.00'),  'Year-end NAV'),
            (alpha,     date(2025, 12, 31), Decimal('350000.00'),  'Wind-down — mostly realized'),
            (beacon,    date(2024, 12, 31), Decimal('3200000.00'), 'Year-end appraisal'),
            (beacon,    date(2025, 12, 31), Decimal('3500000.00'), 'Year-end appraisal — appreciation'),
            (catalyst,  date(2024, 12, 31), Decimal('160000.00'),  'Post-Series-A markups'),
            (catalyst,  date(2025, 12, 31), Decimal('250000.00'),  'Post-Series-B markups'),
            (delta,     date(2024, 12, 31), Decimal('450000.00'),  'Remaining loan book'),
            (delta,     date(2025, 12, 31), Decimal('180000.00'),  'Nearly wound down'),
            (evergreen, date(2024, 12, 31), Decimal('1400000.00'), 'Year-end infrastructure NAV'),
            (evergreen, date(2025, 12, 31), Decimal('1500000.00'), 'Stable cash flows'),
            (frontier,  date(2024, 12, 31), Decimal('400000.00'),  'Early deployment phase'),
            (frontier,  date(2025, 12, 31), Decimal('550000.00'),  'Healthcare portfolio appreciation'),
        ]
        for asset, snap_date, value, note in fmv_data:
            FMVSnapshot.objects.create(
                asset=asset, snapshot_date=snap_date,
                value=value, source='manual', notes=note,
            )

        # ── Summary ──
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(' Seed Data Created (Setup sheet)'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  Entities:      {Entity.objects.count()}')
        self.stdout.write(f'  Assets:        {Asset.objects.count()}')
        self.stdout.write(f'  Ownerships:    {EntityAssetOwnership.objects.count()}')
        self.stdout.write(f'  Tags:          {AssetTag.objects.count()}')
        self.stdout.write(f'  Commitments:   {Commitment.objects.count()}')
        self.stdout.write(f'  Capital Calls: {CapitalCall.objects.count()}')
        self.stdout.write(f'  FMV Snapshots: {FMVSnapshot.objects.count()}')
        self.stdout.write('')
        self.stdout.write('  Next step: Use "Simulate K-1 Upload" in the UI')
        self.stdout.write('  to generate K-1 data → Activity → Reports')
        self.stdout.write('')
