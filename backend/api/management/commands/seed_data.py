from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date
from api.models import Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation


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

        # Assets
        prop1, _ = Asset.objects.get_or_create(
            name='Sunset Apartments', defaults={
                'asset_type': 'property',
                'address': '123 Sunset Blvd, Los Angeles, CA 90028',
                'description': '24-unit apartment complex'
            }
        )
        fund1, _ = Asset.objects.get_or_create(
            name='Growth Equity Fund I', defaults={
                'asset_type': 'fund',
                'description': 'Private equity growth fund'
            }
        )
        stock1, _ = Asset.objects.get_or_create(
            name='Apple Inc.', defaults={
                'asset_type': 'stock',
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

        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {Entity.objects.count()} entities, '
            f'{Asset.objects.count()} assets, '
            f'{Distribution.objects.count()} distributions, '
            f'{DistributionAllocation.objects.count()} allocations.'
        ))
