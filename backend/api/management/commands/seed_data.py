from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
from api.models import (
    Entity, Asset, EntityAssetOwnership, Distribution,
    DistributionAllocation, AssetTag, FMVSnapshot,
)


class Command(BaseCommand):
    help = 'Seed the database with sample data for testing'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding data...')

        # Entities
        alice, _ = Entity.objects.get_or_create(
            name='Alice Johnson', defaults={'entity_type': 'individual', 'email': 'alice@example.com'}
        )
        bob, _ = Entity.objects.get_or_create(
            name='Bob Smith', defaults={'entity_type': 'individual', 'email': 'bob@example.com'}
        )
        abc_llc, _ = Entity.objects.get_or_create(
            name='ABC Investments LLC', defaults={'entity_type': 'LLC', 'email': 'info@abcinv.com'}
        )
        trust, _ = Entity.objects.get_or_create(
            name='Johnson Family Trust', defaults={'entity_type': 'trust'}
        )

        # Assets (using expanded asset_type values)
        prop1, _ = Asset.objects.get_or_create(
            name='Sunset Apartments', defaults={
                'asset_type': 'real_estate',
                'address': '123 Sunset Blvd, Los Angeles, CA 90028',
                'description': '24-unit apartment complex'
            }
        )
        fund1, _ = Asset.objects.get_or_create(
            name='Growth Equity Fund I', defaults={
                'asset_type': 'hedge_fund',
                'description': 'Private equity growth fund'
            }
        )
        stock1, _ = Asset.objects.get_or_create(
            name='Apple Inc.', defaults={
                'asset_type': 'public_equity',
                'ticker_symbol': 'AAPL',
                'description': 'Apple Inc. common stock'
            }
        )

        # Ownerships
        ownerships = [
            (alice, prop1, Decimal('40.0000'), date(2022, 1, 1)),
            (bob, prop1, Decimal('35.0000'), date(2022, 1, 1)),
            (abc_llc, prop1, Decimal('25.0000'), date(2022, 1, 1)),
            (alice, fund1, Decimal('50.0000'), date(2021, 6, 1)),
            (trust, fund1, Decimal('50.0000'), date(2021, 6, 1)),
            (bob, stock1, Decimal('60.0000'), date(2023, 3, 15)),
            (abc_llc, stock1, Decimal('40.0000'), date(2023, 3, 15)),
        ]
        for entity, asset, pct, eff_date in ownerships:
            EntityAssetOwnership.objects.get_or_create(
                entity=entity, asset=asset,
                defaults={'percentage': pct, 'effective_date': eff_date}
            )

        # Distributions & Allocations
        distributions_data = [
            # (asset, date, total, type, [(entity, amount, pct)])
            (prop1, date(2024, 3, 31), Decimal('48000.00'), 'regular', [
                (alice, Decimal('19200.00'), Decimal('40.0000')),
                (bob, Decimal('16800.00'), Decimal('35.0000')),
                (abc_llc, Decimal('12000.00'), Decimal('25.0000')),
            ]),
            (prop1, date(2024, 6, 30), Decimal('52000.00'), 'regular', [
                (alice, Decimal('20800.00'), Decimal('40.0000')),
                (bob, Decimal('18200.00'), Decimal('35.0000')),
                (abc_llc, Decimal('13000.00'), Decimal('25.0000')),
            ]),
            (prop1, date(2024, 9, 30), Decimal('50000.00'), 'regular', [
                (alice, Decimal('20000.00'), Decimal('40.0000')),
                (bob, Decimal('17500.00'), Decimal('35.0000')),
                (abc_llc, Decimal('12500.00'), Decimal('25.0000')),
            ]),
            (prop1, date(2024, 12, 31), Decimal('55000.00'), 'regular', [
                (alice, Decimal('22000.00'), Decimal('40.0000')),
                (bob, Decimal('19250.00'), Decimal('35.0000')),
                (abc_llc, Decimal('13750.00'), Decimal('25.0000')),
            ]),
            (fund1, date(2024, 6, 15), Decimal('100000.00'), 'regular', [
                (alice, Decimal('50000.00'), Decimal('50.0000')),
                (trust, Decimal('50000.00'), Decimal('50.0000')),
            ]),
            (fund1, date(2024, 12, 15), Decimal('75000.00'), 'special', [
                (alice, Decimal('37500.00'), Decimal('50.0000')),
                (trust, Decimal('37500.00'), Decimal('50.0000')),
            ]),
            (stock1, date(2024, 3, 15), Decimal('12000.00'), 'regular', [
                (bob, Decimal('7200.00'), Decimal('60.0000')),
                (abc_llc, Decimal('4800.00'), Decimal('40.0000')),
            ]),
            (stock1, date(2024, 9, 15), Decimal('13500.00'), 'regular', [
                (bob, Decimal('8100.00'), Decimal('60.0000')),
                (abc_llc, Decimal('5400.00'), Decimal('40.0000')),
            ]),
        ]

        for asset, dist_date, total, dist_type, allocs in distributions_data:
            dist, created = Distribution.objects.get_or_create(
                asset=asset, distribution_date=dist_date,
                defaults={'total_amount': total, 'distribution_type': dist_type}
            )
            if created:
                for entity, amount, pct in allocs:
                    DistributionAllocation.objects.create(
                        distribution=dist, entity=entity, amount=amount, percentage=pct
                    )

        # Asset Tags
        tag_domestic, _ = AssetTag.objects.get_or_create(
            name='Domestic', defaults={'slug': 'domestic', 'color': '#3B82F6'}
        )
        tag_illiquid, _ = AssetTag.objects.get_or_create(
            name='Illiquid', defaults={'slug': 'illiquid', 'color': '#EF4444'}
        )
        tag_income, _ = AssetTag.objects.get_or_create(
            name='Income Producing', defaults={'slug': 'income-producing', 'color': '#10B981'}
        )
        tag_growth, _ = AssetTag.objects.get_or_create(
            name='Growth', defaults={'slug': 'growth', 'color': '#8B5CF6'}
        )
        tag_core, _ = AssetTag.objects.get_or_create(
            name='Core Holding', defaults={'slug': 'core-holding', 'color': '#F59E0B'}
        )

        # Assign tags to assets
        prop1.tags.add(tag_domestic, tag_illiquid, tag_income)
        fund1.tags.add(tag_illiquid, tag_growth)
        stock1.tags.add(tag_domestic, tag_growth, tag_core)

        # FMV Snapshots — quarterly history for meaningful TWR/IRR computation
        today = date.today()
        fmv_data = [
            # (asset, [(months_ago, value), ...])
            (prop1, [
                (18, Decimal('2800000.00')),
                (15, Decimal('2850000.00')),
                (12, Decimal('2900000.00')),
                (9, Decimal('2950000.00')),
                (6, Decimal('3000000.00')),
                (3, Decimal('3050000.00')),
                (0, Decimal('3100000.00')),
            ]),
            (fund1, [
                (18, Decimal('1500000.00')),
                (15, Decimal('1520000.00')),
                (12, Decimal('1480000.00')),
                (9, Decimal('1550000.00')),
                (6, Decimal('1600000.00')),
                (3, Decimal('1650000.00')),
                (0, Decimal('1700000.00')),
            ]),
            (stock1, [
                (18, Decimal('450000.00')),
                (15, Decimal('475000.00')),
                (12, Decimal('460000.00')),
                (9, Decimal('510000.00')),
                (6, Decimal('530000.00')),
                (3, Decimal('520000.00')),
                (0, Decimal('550000.00')),
            ]),
        ]
        for asset, snapshots in fmv_data:
            for months_ago, value in snapshots:
                snap_date = today - timedelta(days=months_ago * 30)
                FMVSnapshot.objects.get_or_create(
                    asset=asset,
                    snapshot_date=snap_date,
                    defaults={'value': value, 'source': 'manual'},
                )

        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {Entity.objects.count()} entities, '
            f'{Asset.objects.count()} assets, '
            f'{Distribution.objects.count()} distributions, '
            f'{DistributionAllocation.objects.count()} allocations, '
            f'{AssetTag.objects.count()} tags, '
            f'{FMVSnapshot.objects.count()} FMV snapshots.'
        ))
