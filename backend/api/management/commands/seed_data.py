"""
Seed the database with educational test data for the Portfolio Tracker.

Clears ALL existing data, then creates 4 entities with varied investment
scenarios that exercise every column in the Portfolio Summary:

  Entity                      | Scenario
  ----------------------------|--------------------------------------------------
  Acme Capital Partners       | Fully called, fully realized (DPI=2.0, RVPI=0)
  Blue Harbor Family Trust    | Partially called, mixed (DPI~0.5, RVPI~1.2)
  Cypress Growth Holdings     | Early-stage, unrealized only (DPI=0, RVPI~1.5)
  Drake Equity Group          | Mature, mostly realized (DPI~1.8, RVPI~0.1)

Metric definitions:
  - Original Commitment: Total $ pledged to a fund
  - % Called: Paid-In / Original Commitment
  - Unfunded Commitment: Original Commitment - Paid-In
  - Paid-In (ABS): Capital calls actually drawn
  - Distributions: Cash returned to the investor
  - Residual Value: Current market value of remaining holdings
  - DPI (Distributions to Paid-In): Distributions / Paid-In  -- "cash-on-cash"
  - RVPI (Residual Value to Paid-In): Residual / Paid-In  -- unrealized value
  - TVPI (Total Value to Paid-In): (Distributions + Residual) / Paid-In  -- total multiple
  - IRR (XIRR): Time-weighted annualized return considering cash flow timing
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date


class Command(BaseCommand):
    help = 'Clear all data and seed with educational portfolio test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-clear', action='store_true',
            help='Skip clearing existing data (append instead)',
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        from api.models import (
            Entity, Asset, EntityAssetOwnership, Distribution,
            DistributionAllocation, AssetTag, FMVSnapshot,
            Budget, BudgetLineItem, Commitment, CapitalCall,
        )

        if not kwargs.get('no_clear'):
            self.stdout.write('Clearing all existing data...')
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
            # Also clear Plaid data if present
            try:
                from plaid_integration.models import PlaidAccount, PlaidItem
                PlaidAccount.objects.all().delete()
                PlaidItem.objects.all().delete()
            except Exception:
                pass
            self.stdout.write(self.style.WARNING('  All tables cleared.'))

        self.stdout.write('Creating educational seed data...')

        # Tags
        tag_pe = AssetTag.objects.create(name='Private Equity', slug='private-equity', color='#8B5CF6')
        tag_vc = AssetTag.objects.create(name='Venture Capital', slug='venture-capital', color='#3B82F6')
        tag_re = AssetTag.objects.create(name='Real Estate', slug='real-estate', color='#10B981')
        tag_growth = AssetTag.objects.create(name='Growth', slug='growth', color='#F59E0B')
        tag_income = AssetTag.objects.create(name='Income', slug='income', color='#EF4444')

        # ── Entities ──
        acme = Entity.objects.create(
            name='Acme Capital Partners',
            entity_type='LLC',
            description='Fully realized PE fund - 2x cash return, zero residual.',
            email='acme@example.com',
        )
        blue = Entity.objects.create(
            name='Blue Harbor Family Trust',
            entity_type='trust',
            description='Partially called fund - mix of distributions and unrealized gains.',
            email='blue@example.com',
        )
        cypress = Entity.objects.create(
            name='Cypress Growth Holdings',
            entity_type='company',
            description='Early-stage VC - no distributions yet, growing residual (J-curve).',
            email='cypress@example.com',
        )
        drake = Entity.objects.create(
            name='Drake Equity Group',
            entity_type='partnership',
            description='Mature fund - mostly distributed, small residual tail.',
            email='drake@example.com',
        )

        # ── Assets ──
        fund_alpha = Asset.objects.create(
            name='Alpha Buyout Fund III',
            asset_type='private_equity',
            description='Large-cap buyout fund (vintage 2020). Fully realized.',
        )
        fund_alpha.tags.add(tag_pe, tag_income)

        fund_beacon = Asset.objects.create(
            name='Beacon Real Assets II',
            asset_type='real_estate',
            description='Core-plus real estate fund (vintage 2022). Still deploying.',
        )
        fund_beacon.tags.add(tag_re, tag_income)

        fund_catalyst = Asset.objects.create(
            name='Catalyst Ventures IV',
            asset_type='private_equity',
            description='Early-stage venture fund (vintage 2023). Pre-distribution.',
        )
        fund_catalyst.tags.add(tag_vc, tag_growth)

        fund_delta = Asset.objects.create(
            name='Delta Credit Opportunities I',
            asset_type='fixed_income',
            description='Distressed / special situations fund (vintage 2019). Wind-down phase.',
        )
        fund_delta.tags.add(tag_pe, tag_income)

        stock_spy = Asset.objects.create(
            name='S&P 500 Index Fund',
            asset_type='public_equity',
            ticker_symbol='SPY',
            description='Passive index tracking. Owned by Blue Harbor.',
        )
        stock_spy.tags.add(tag_growth)

        # ── Ownerships (100% per entity-fund for clarity) ──
        EntityAssetOwnership.objects.create(
            entity=acme, asset=fund_alpha,
            percentage=Decimal('100.0000'), effective_date=date(2020, 3, 1),
        )
        EntityAssetOwnership.objects.create(
            entity=blue, asset=fund_beacon,
            percentage=Decimal('100.0000'), effective_date=date(2022, 6, 1),
        )
        EntityAssetOwnership.objects.create(
            entity=blue, asset=stock_spy,
            percentage=Decimal('100.0000'), effective_date=date(2022, 1, 1),
        )
        EntityAssetOwnership.objects.create(
            entity=cypress, asset=fund_catalyst,
            percentage=Decimal('100.0000'), effective_date=date(2023, 1, 15),
        )
        EntityAssetOwnership.objects.create(
            entity=drake, asset=fund_delta,
            percentage=Decimal('100.0000'), effective_date=date(2019, 9, 1),
        )

        # ════════════════════════════════════════════════════════════════
        # 1) ACME - Alpha Buyout Fund III
        #    Commitment: $1,000,000   Fully called (100%)
        #    Distributions: $2,000,000  Residual: $0
        #    DPI=2.00  RVPI=0.00  TVPI=2.00
        # ════════════════════════════════════════════════════════════════
        commit_acme = Commitment.objects.create(
            entity=acme, asset=fund_alpha,
            commitment_date=date(2020, 3, 1),
            original_amount=Decimal('1000000.00'),
            notes='$1M commitment, fully called over 2020-2021.',
        )
        CapitalCall.objects.create(
            commitment=commit_acme, call_date=date(2020, 4, 1),
            amount=Decimal('300000.00'), notes='Initial draw - 30%',
        )
        CapitalCall.objects.create(
            commitment=commit_acme, call_date=date(2020, 9, 1),
            amount=Decimal('300000.00'), notes='Second draw - 30%',
        )
        CapitalCall.objects.create(
            commitment=commit_acme, call_date=date(2021, 3, 1),
            amount=Decimal('250000.00'), notes='Third draw - 25%',
        )
        CapitalCall.objects.create(
            commitment=commit_acme, call_date=date(2021, 9, 1),
            amount=Decimal('150000.00'), notes='Final draw - 15%',
        )

        # Distributions: $2,000,000 total (DPI = 2.0x)
        for dt, amt, dtype, note in [
            (date(2022, 6, 15), Decimal('400000.00'), 'regular', 'Partial realization - portfolio company A exit.'),
            (date(2023, 3, 15), Decimal('600000.00'), 'regular', 'Portfolio company B IPO proceeds.'),
            (date(2024, 1, 15), Decimal('500000.00'), 'special', 'Final liquidation - remaining portfolio.'),
            (date(2024, 12, 1), Decimal('500000.00'), 'liquidating', 'Wind-down distribution.'),
        ]:
            d = Distribution.objects.create(
                asset=fund_alpha, distribution_date=dt,
                total_amount=amt, distribution_type=dtype, notes=note,
            )
            DistributionAllocation.objects.create(
                distribution=d, entity=acme,
                amount=amt, percentage=Decimal('100.0000'),
            )

        # FMV: Fund is fully realized
        FMVSnapshot.objects.create(
            asset=fund_alpha, snapshot_date=date(2025, 12, 31),
            value=Decimal('0.00'), source='manual',
            notes='Fund fully liquidated.',
        )

        # ════════════════════════════════════════════════════════════════
        # 2) BLUE HARBOR - Beacon Real Assets II
        #    Commitment: $2,000,000   75% called -> Paid-in $1,500,000
        #    Distributions: $750,000   Residual: $1,800,000
        #    DPI=0.50  RVPI=1.20  TVPI=1.70
        # ════════════════════════════════════════════════════════════════
        commit_blue = Commitment.objects.create(
            entity=blue, asset=fund_beacon,
            commitment_date=date(2022, 6, 1),
            original_amount=Decimal('2000000.00'),
            notes='$2M commitment to real estate fund. 75% called to date.',
        )
        CapitalCall.objects.create(
            commitment=commit_blue, call_date=date(2022, 7, 1),
            amount=Decimal('500000.00'), notes='Initial draw - 25%',
        )
        CapitalCall.objects.create(
            commitment=commit_blue, call_date=date(2023, 1, 1),
            amount=Decimal('500000.00'), notes='Second draw - 25%',
        )
        CapitalCall.objects.create(
            commitment=commit_blue, call_date=date(2023, 7, 1),
            amount=Decimal('500000.00'), notes='Third draw - 25%',
        )

        # Distributions: $750,000 total
        for dt, amt, note in [
            (date(2024, 3, 31), Decimal('375000.00'), 'Quarterly income distribution.'),
            (date(2024, 9, 30), Decimal('375000.00'), 'Quarterly income distribution.'),
        ]:
            d = Distribution.objects.create(
                asset=fund_beacon, distribution_date=dt,
                total_amount=amt, distribution_type='regular', notes=note,
            )
            DistributionAllocation.objects.create(
                distribution=d, entity=blue,
                amount=amt, percentage=Decimal('100.0000'),
            )

        # FMV snapshots
        FMVSnapshot.objects.create(
            asset=fund_beacon, snapshot_date=date(2024, 6, 30),
            value=Decimal('1500000.00'), source='manual',
            notes='Mid-year appraisal.',
        )
        FMVSnapshot.objects.create(
            asset=fund_beacon, snapshot_date=date(2025, 12, 31),
            value=Decimal('1800000.00'), source='manual',
            notes='Year-end appraisal - appreciation on core properties.',
        )

        # SPY index fund for Blue Harbor (adds to asset class summary)
        FMVSnapshot.objects.create(
            asset=stock_spy, snapshot_date=date(2025, 6, 30),
            value=Decimal('480000.00'), source='manual',
            notes='Mid-year market value.',
        )
        FMVSnapshot.objects.create(
            asset=stock_spy, snapshot_date=date(2025, 12, 31),
            value=Decimal('520000.00'), source='manual',
            notes='Year-end market value.',
        )

        # ════════════════════════════════════════════════════════════════
        # 3) CYPRESS - Catalyst Ventures IV
        #    Commitment: $500,000   60% called -> Paid-in $300,000
        #    Distributions: $0   Residual: $450,000
        #    DPI=0.00  RVPI=1.50  TVPI=1.50
        #    (J-curve: all value is unrealized)
        # ════════════════════════════════════════════════════════════════
        commit_cypress = Commitment.objects.create(
            entity=cypress, asset=fund_catalyst,
            commitment_date=date(2023, 1, 15),
            original_amount=Decimal('500000.00'),
            notes='$500K VC commitment. Still in investment period.',
        )
        CapitalCall.objects.create(
            commitment=commit_cypress, call_date=date(2023, 3, 1),
            amount=Decimal('100000.00'), notes='Initial draw - 20%',
        )
        CapitalCall.objects.create(
            commitment=commit_cypress, call_date=date(2023, 9, 1),
            amount=Decimal('100000.00'), notes='Second draw - 20%',
        )
        CapitalCall.objects.create(
            commitment=commit_cypress, call_date=date(2024, 6, 1),
            amount=Decimal('100000.00'), notes='Third draw - 20%',
        )
        # No distributions - typical for early VC

        FMVSnapshot.objects.create(
            asset=fund_catalyst, snapshot_date=date(2024, 6, 30),
            value=Decimal('350000.00'), source='manual',
            notes='Mid-year NAV statement.',
        )
        FMVSnapshot.objects.create(
            asset=fund_catalyst, snapshot_date=date(2025, 12, 31),
            value=Decimal('450000.00'), source='manual',
            notes='Year-end NAV - Series B markups driving appreciation.',
        )

        # ════════════════════════════════════════════════════════════════
        # 4) DRAKE - Delta Credit Opportunities I
        #    Commitment: $3,000,000   100% called -> Paid-in $3,000,000
        #    Distributions: $5,400,000   Residual: $300,000
        #    DPI=1.80  RVPI=0.10  TVPI=1.90
        # ════════════════════════════════════════════════════════════════
        commit_drake = Commitment.objects.create(
            entity=drake, asset=fund_delta,
            commitment_date=date(2019, 9, 1),
            original_amount=Decimal('3000000.00'),
            notes='$3M credit fund commitment. Fully called. Winding down.',
        )
        CapitalCall.objects.create(
            commitment=commit_drake, call_date=date(2019, 10, 1),
            amount=Decimal('1000000.00'), notes='Initial draw - 33%',
        )
        CapitalCall.objects.create(
            commitment=commit_drake, call_date=date(2020, 4, 1),
            amount=Decimal('1000000.00'), notes='Second draw - 33%',
        )
        CapitalCall.objects.create(
            commitment=commit_drake, call_date=date(2020, 10, 1),
            amount=Decimal('1000000.00'), notes='Final draw - 34%',
        )

        # Distributions: $5,400,000 total over several years
        for dt, amt, dtype, note in [
            (date(2021, 3, 31), Decimal('600000.00'), 'regular', 'Q1 2021 interest + principal'),
            (date(2021, 9, 30), Decimal('600000.00'), 'regular', 'Q3 2021'),
            (date(2022, 3, 31), Decimal('800000.00'), 'regular', 'Q1 2022 - recovery rally'),
            (date(2022, 9, 30), Decimal('800000.00'), 'regular', 'Q3 2022'),
            (date(2023, 3, 31), Decimal('700000.00'), 'regular', 'Q1 2023'),
            (date(2023, 9, 30), Decimal('700000.00'), 'regular', 'Q3 2023'),
            (date(2024, 6, 30), Decimal('600000.00'), 'return_of_capital', '2024 - wind-down return'),
            (date(2025, 3, 31), Decimal('600000.00'), 'liquidating', 'Final liquidation proceeds'),
        ]:
            d = Distribution.objects.create(
                asset=fund_delta, distribution_date=dt,
                total_amount=amt, distribution_type=dtype, notes=note,
            )
            DistributionAllocation.objects.create(
                distribution=d, entity=drake,
                amount=amt, percentage=Decimal('100.0000'),
            )

        # FMV snapshots
        FMVSnapshot.objects.create(
            asset=fund_delta, snapshot_date=date(2025, 6, 30),
            value=Decimal('400000.00'), source='manual',
            notes='Remaining loan book - mid-year.',
        )
        FMVSnapshot.objects.create(
            asset=fund_delta, snapshot_date=date(2025, 12, 31),
            value=Decimal('300000.00'), source='manual',
            notes='Year-end - most loans paid off, small tail remaining.',
        )

        # ── Summary output ──
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(' Educational Seed Data Created'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(f'  Entities:       {Entity.objects.count()}')
        self.stdout.write(f'  Assets:         {Asset.objects.count()}')
        self.stdout.write(f'  Commitments:    {Commitment.objects.count()}')
        self.stdout.write(f'  Capital Calls:  {CapitalCall.objects.count()}')
        self.stdout.write(f'  Distributions:  {Distribution.objects.count()}')
        self.stdout.write(f'  Allocations:    {DistributionAllocation.objects.count()}')
        self.stdout.write(f'  FMV Snapshots:  {FMVSnapshot.objects.count()}')
        self.stdout.write(f'  Ownerships:     {EntityAssetOwnership.objects.count()}')
        self.stdout.write(f'  Tags:           {AssetTag.objects.count()}')
        self.stdout.write('')
        self.stdout.write('  Expected Portfolio Summary:')
        self.stdout.write('  Entity                    | Commit.  | %Called | Unfunded | Paid-In | Distrib. | Residual | DPI  | RVPI | TVPI')
        self.stdout.write('  --------------------------|----------|--------|----------|---------|----------|----------|------|------|------')
        self.stdout.write('  Acme Capital Partners     |   $1.0M  |  100%  |    $0    |  $1.0M  |  $2.0M   |    $0    | 2.00 | 0.00 | 2.00')
        self.stdout.write('  Blue Harbor Family Trust  |   $2.0M  |   75%  |  $0.5M   |  $1.5M  |  $0.75M  |  $1.8M   | 0.50 | 1.20 | 1.70')
        self.stdout.write('  Cypress Growth Holdings   |   $0.5M  |   60%  |  $0.2M   |  $0.3M  |    $0    |  $0.45M  | 0.00 | 1.50 | 1.50')
        self.stdout.write('  Drake Equity Group        |   $3.0M  |  100%  |    $0    |  $3.0M  |  $5.4M   |  $0.3M   | 1.80 | 0.10 | 1.90')
        self.stdout.write('  All Entities              |   $6.5M  |   89%  |  $0.7M   |  $5.8M  |  $8.15M  |  $2.55M  | 1.41 | 0.44 | 1.85')
        self.stdout.write('')
        self.stdout.write('  Metric Guide:')
        self.stdout.write('    DPI  = Distributions / Paid-In  (cash-on-cash return)')
        self.stdout.write('    RVPI = Residual / Paid-In       (unrealized value remaining)')
        self.stdout.write('    TVPI = (Dist + Residual) / Paid-In  (total value multiple)')
        self.stdout.write('    IRR  = Time-weighted annualized return (XIRR)')
        self.stdout.write('')
