from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import datetime

from .models import Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation, Budget, BudgetLineItem, AssetTag, FMVSnapshot
from .performance import calculate_twr, calculate_xirr, calculate_asset_irr, resolve_period, annualize_return


class EntityAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_entity(self):
        data = {
            'name': 'Test Corp',
            'entity_type': 'company',
            'email': 'test@testcorp.com',
        }
        response = self.client.post('/api/entities/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Corp')
        self.assertEqual(response.data['entity_type'], 'company')

    def test_list_entities(self):
        Entity.objects.create(name='Corp A', entity_type='company')
        Entity.objects.create(name='Corp B', entity_type='LLC')
        response = self.client.get('/api/entities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_get_entity(self):
        entity = Entity.objects.create(name='Alpha LLC', entity_type='LLC')
        response = self.client.get(f'/api/entities/{entity.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Alpha LLC')

    def test_update_entity(self):
        entity = Entity.objects.create(name='Old Name', entity_type='individual')
        response = self.client.patch(
            f'/api/entities/{entity.id}/',
            {'name': 'New Name'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'New Name')

    def test_delete_entity(self):
        entity = Entity.objects.create(name='To Delete', entity_type='other')
        response = self.client.delete(f'/api/entities/{entity.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class AssetAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_property_asset(self):
        data = {
            'name': '123 Main St',
            'asset_type': 'real_estate',
            'address': '123 Main St, Springfield, IL',
        }
        response = self.client.post('/api/assets/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['asset_type'], 'real_estate')

    def test_create_stock_asset(self):
        data = {
            'name': 'Apple Inc',
            'asset_type': 'public_equity',
            'ticker_symbol': 'AAPL',
        }
        response = self.client.post('/api/assets/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ticker_symbol'], 'AAPL')


class OwnershipAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Investor A', entity_type='individual')
        self.asset = Asset.objects.create(name='Property X', asset_type='real_estate')

    def test_create_ownership(self):
        data = {
            'entity': self.entity.id,
            'asset': self.asset.id,
            'percentage': '50.0000',
            'effective_date': '2024-01-01',
        }
        response = self.client.post('/api/ownerships/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['percentage']), Decimal('50.0000'))


class DistributionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Partner A', entity_type='individual')
        self.asset = Asset.objects.create(name='Property A', asset_type='real_estate')

    def test_create_distribution(self):
        data = {
            'asset': self.asset.id,
            'distribution_date': '2024-06-15',
            'total_amount': '10000.00',
            'distribution_type': 'regular',
            'allocations': [
                {
                    'entity': self.entity.id,
                    'amount': '10000.00',
                    'percentage': '100.0000',
                }
            ]
        }
        response = self.client.post('/api/distributions/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['total_amount']), Decimal('10000.00'))

    def test_list_distributions(self):
        dist = Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2024, 6, 15),
            total_amount=Decimal('5000.00'),
            distribution_type='regular'
        )
        response = self.client.get('/api/distributions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ReportGenerationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Test Entity', entity_type='LLC')
        self.asset = Asset.objects.create(name='Test Property', asset_type='real_estate')
        EntityAssetOwnership.objects.create(
            entity=self.entity,
            asset=self.asset,
            percentage=Decimal('100.0000'),
            effective_date=datetime.date(2024, 1, 1)
        )
        self.dist = Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2024, 3, 15),
            total_amount=Decimal('10000.00'),
            distribution_type='regular'
        )
        DistributionAllocation.objects.create(
            distribution=self.dist,
            entity=self.entity,
            amount=Decimal('10000.00'),
            percentage=Decimal('100.0000')
        )

    def test_generate_yearly_report(self):
        data = {
            'period_type': 'yearly',
            'year': 2024,
        }
        response = self.client.post('/api/reports/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)
        self.assertIn('distribution_count', response.data['summary'])
        self.assertIn('by_entity', response.data)
        self.assertIn('by_asset', response.data)

    def test_generate_quarterly_report(self):
        data = {
            'period_type': 'quarterly',
            'year': 2024,
            'quarter': 1,
        }
        response = self.client.post('/api/reports/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)

    def test_generate_monthly_report(self):
        data = {
            'period_type': 'monthly',
            'year': 2024,
            'month': 3,
        }
        response = self.client.post('/api/reports/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_report(self):
        data = {
            'period_type': 'yearly',
            'year': 2024,
        }
        response = self.client.post('/api/reports/export/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


class BudgetAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Budget Entity', entity_type='LLC')
        self.asset = Asset.objects.create(name='Budget Property', asset_type='real_estate')

    def test_create_budget(self):
        data = {
            'name': 'FY2024 Budget',
            'year': 2024,
            'period_type': 'yearly',
            'line_items': [
                {
                    'asset': self.asset.id,
                    'entity': self.entity.id,
                    'amount': '50000.00',
                }
            ]
        }
        response = self.client.post('/api/budgets/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'FY2024 Budget')

    def test_list_budgets(self):
        Budget.objects.create(name='Budget A', year=2024, period_type='yearly')
        Budget.objects.create(name='Budget B', year=2024, period_type='quarterly', quarter=1)
        response = self.client.get('/api/budgets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_get_budget_with_line_items(self):
        budget = Budget.objects.create(name='Detail Budget', year=2024, period_type='yearly')
        BudgetLineItem.objects.create(
            budget=budget, asset=self.asset, entity=self.entity,
            amount=Decimal('25000.00')
        )
        response = self.client.get(f'/api/budgets/{budget.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['line_items']), 1)
        self.assertEqual(Decimal(response.data['line_items'][0]['amount']), Decimal('25000.00'))

    def test_update_budget(self):
        budget = Budget.objects.create(name='Old Budget', year=2024, period_type='yearly')
        response = self.client.patch(
            f'/api/budgets/{budget.id}/',
            {'name': 'Updated Budget'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Budget')

    def test_delete_budget(self):
        budget = Budget.objects.create(name='Delete Me', year=2024, period_type='yearly')
        response = self.client.delete(f'/api/budgets/{budget.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class AutoAllocateTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.asset = Asset.objects.create(name='Auto Alloc Property', asset_type='real_estate')
        self.entity_a = Entity.objects.create(name='Entity A', entity_type='LLC')
        self.entity_b = Entity.objects.create(name='Entity B', entity_type='LLC')
        self.dist = Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2024, 6, 1),
            total_amount=Decimal('1000.00'),
            distribution_type='regular',
        )

    def test_auto_allocate_success(self):
        EntityAssetOwnership.objects.create(
            entity=self.entity_a, asset=self.asset,
            percentage=Decimal('60.0000'), effective_date=datetime.date(2024, 1, 1),
        )
        EntityAssetOwnership.objects.create(
            entity=self.entity_b, asset=self.asset,
            percentage=Decimal('40.0000'), effective_date=datetime.date(2024, 1, 1),
        )
        response = self.client.post(f'/api/distributions/{self.dist.id}/auto-allocate/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        allocations = response.data['allocations']
        self.assertEqual(len(allocations), 2)
        total = sum(Decimal(a['amount']) for a in allocations)
        self.assertEqual(total, self.dist.total_amount)

    def test_auto_allocate_no_ownerships_returns_400(self):
        response = self.client.post(f'/api/distributions/{self.dist.id}/auto-allocate/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class YoYAndRetainedEarningsReportTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='YoY Entity', entity_type='LLC')
        self.asset = Asset.objects.create(name='YoY Property', asset_type='real_estate')

        # Prior year distribution (2023)
        dist_prior = Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2023, 6, 15),
            total_amount=Decimal('8000.00'),
            distribution_type='regular',
        )
        DistributionAllocation.objects.create(
            distribution=dist_prior, entity=self.entity,
            amount=Decimal('8000.00'), percentage=Decimal('100.0000'),
        )

        # Current year distribution (2024)
        dist_current = Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2024, 6, 15),
            total_amount=Decimal('10000.00'),
            distribution_type='regular',
        )
        DistributionAllocation.objects.create(
            distribution=dist_current, entity=self.entity,
            amount=Decimal('10000.00'), percentage=Decimal('100.0000'),
        )

    def test_report_includes_yoy_comparison(self):
        data = {'period_type': 'yearly', 'year': 2024}
        response = self.client.post('/api/reports/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        yoy = response.data['yoy_comparison']
        self.assertIsNotNone(yoy)
        self.assertEqual(yoy['current_year'], 2024)
        self.assertEqual(yoy['prior_year'], 2023)
        self.assertEqual(yoy['total_current'], '10000.00')
        self.assertEqual(yoy['total_prior'], '8000.00')
        self.assertEqual(yoy['total_change'], '2000.00')
        self.assertIsNotNone(yoy['total_change_pct'])
        self.assertIn('by_entity', yoy)
        self.assertIn('by_asset', yoy)

    def test_report_includes_retained_earnings(self):
        data = {'period_type': 'yearly', 'year': 2024}
        response = self.client.post('/api/reports/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        re = response.data['retained_earnings']
        self.assertIsNotNone(re)
        self.assertEqual(re['year'], 2024)
        self.assertIn('by_entity', re)
        entity_row = next((r for r in re['by_entity'] if r['entity_name'] == 'YoY Entity'), None)
        self.assertIsNotNone(entity_row)
        self.assertEqual(entity_row['beginning_balance'], '8000.00')
        self.assertEqual(entity_row['current_year_distributions'], '10000.00')
        self.assertEqual(entity_row['ending_balance'], '18000.00')
        self.assertEqual(re['total_beginning_balance'], '8000.00')
        self.assertEqual(re['total_current_year'], '10000.00')
        self.assertEqual(re['total_ending_balance'], '18000.00')


class BudgetVsActualReportTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Report Entity', entity_type='LLC')
        self.asset = Asset.objects.create(name='Report Property', asset_type='real_estate')

        # Create a budget
        self.budget = Budget.objects.create(
            name='FY2024 Budget', year=2024, period_type='yearly'
        )
        BudgetLineItem.objects.create(
            budget=self.budget, asset=self.asset, entity=self.entity,
            amount=Decimal('50000.00')
        )

        # Create actual distribution
        dist = Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2024, 6, 15),
            total_amount=Decimal('45000.00'),
            distribution_type='regular'
        )
        DistributionAllocation.objects.create(
            distribution=dist, entity=self.entity,
            amount=Decimal('45000.00'), percentage=Decimal('100.0000')
        )

    def test_report_includes_budget_comparison(self):
        data = {'period_type': 'yearly', 'year': 2024}
        response = self.client.post('/api/reports/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('budget_comparison', response.data)
        bc = response.data['budget_comparison']
        self.assertIsNotNone(bc)
        self.assertEqual(bc['budget_name'], 'FY2024 Budget')
        self.assertEqual(bc['total_budgeted'], '50000.00')
        self.assertEqual(bc['total_actual'], '45000.00')
        self.assertEqual(bc['total_variance'], '-5000.00')

    def test_report_no_budget_returns_null(self):
        data = {'period_type': 'yearly', 'year': 2020}
        response = self.client.post('/api/reports/generate/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['budget_comparison'])


# ═══════════════════════════════════════════════════════════════════════
# T057: FMVSnapshot & AssetTag model validation tests
# ═══════════════════════════════════════════════════════════════════════

class FMVSnapshotModelTest(TestCase):
    def setUp(self):
        self.asset = Asset.objects.create(name='Test Asset', asset_type='real_estate')

    def test_create_valid_snapshot(self):
        snap = FMVSnapshot.objects.create(
            asset=self.asset,
            snapshot_date=datetime.date(2024, 6, 1),
            value=Decimal('1000000.00'),
        )
        self.assertEqual(snap.value, Decimal('1000000.00'))
        self.assertEqual(snap.source, 'manual')

    def test_negative_value_validation(self):
        snap = FMVSnapshot(
            asset=self.asset,
            snapshot_date=datetime.date(2024, 6, 1),
            value=Decimal('-100.00'),
        )
        with self.assertRaises(ValidationError) as ctx:
            snap.clean()
        self.assertIn('value', ctx.exception.message_dict)

    def test_future_date_validation(self):
        future = datetime.date.today() + datetime.timedelta(days=30)
        snap = FMVSnapshot(
            asset=self.asset,
            snapshot_date=future,
            value=Decimal('1000.00'),
        )
        with self.assertRaises(ValidationError) as ctx:
            snap.clean()
        self.assertIn('snapshot_date', ctx.exception.message_dict)

    def test_unique_constraint(self):
        FMVSnapshot.objects.create(
            asset=self.asset,
            snapshot_date=datetime.date(2024, 6, 1),
            value=Decimal('1000.00'),
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            FMVSnapshot.objects.create(
                asset=self.asset,
                snapshot_date=datetime.date(2024, 6, 1),
                value=Decimal('2000.00'),
            )

    def test_zero_value_is_valid(self):
        snap = FMVSnapshot(
            asset=self.asset,
            snapshot_date=datetime.date(2024, 1, 1),
            value=Decimal('0.00'),
        )
        snap.clean()  # Should not raise


class AssetTagModelTest(TestCase):
    def test_slug_auto_generation(self):
        tag = AssetTag.objects.create(name='Core Holding', color='#3B82F6')
        self.assertEqual(tag.slug, 'core-holding')

    def test_color_regex_validation(self):
        tag = AssetTag(name='Bad Color', color='not-hex')
        with self.assertRaises(ValidationError) as ctx:
            tag.clean()
        self.assertIn('color', ctx.exception.message_dict)

    def test_valid_hex_color(self):
        tag = AssetTag(name='Valid Color', color='#FF00AA')
        tag.clean()  # Should not raise

    def test_unique_name_case_insensitive(self):
        AssetTag.objects.create(name='Domestic', color='#3B82F6')
        tag2 = AssetTag(name='domestic', color='#EF4444')
        with self.assertRaises(ValidationError):
            tag2.clean()


# ═══════════════════════════════════════════════════════════════════════
# T058: FMV CRUD API tests
# ═══════════════════════════════════════════════════════════════════════

class FMVSnapshotAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.asset = Asset.objects.create(name='FMV Test Asset', asset_type='real_estate')

    def test_create_snapshot(self):
        data = {
            'asset': self.asset.id,
            'snapshot_date': '2024-06-01',
            'value': '500000.00',
            'source': 'manual',
        }
        response = self.client.post('/api/fmv-snapshots/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['value'], '500000.00')

    def test_list_snapshots(self):
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100.00'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 6, 1), value=Decimal('200.00'))
        response = self.client.get('/api/fmv-snapshots/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_filter_by_asset(self):
        other_asset = Asset.objects.create(name='Other', asset_type='cash')
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100.00'))
        FMVSnapshot.objects.create(asset=other_asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('200.00'))
        response = self.client.get(f'/api/fmv-snapshots/?asset={self.asset.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only contain snapshots for self.asset
        results = response.data if isinstance(response.data, list) else response.data.get('results', response.data)
        for snap in results:
            self.assertEqual(snap['asset'], self.asset.id)

    def test_filter_by_date_range(self):
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100.00'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 6, 1), value=Decimal('200.00'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 12, 1), value=Decimal('300.00'))
        response = self.client.get(f'/api/fmv-snapshots/?asset={self.asset.id}&date_from=2024-03-01&date_to=2024-09-01')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', response.data)
        # Only the June 2024 snapshot should match
        matching = [s for s in results if s['snapshot_date'] == '2024-06-01']
        self.assertGreaterEqual(len(matching), 1)

    def test_update_snapshot(self):
        snap = FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100.00'))
        response = self.client.patch(f'/api/fmv-snapshots/{snap.id}/', {'value': '250.00'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['value'], '250.00')

    def test_delete_snapshot(self):
        snap = FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100.00'))
        response = self.client.delete(f'/api/fmv-snapshots/{snap.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_duplicate_date_fails(self):
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100.00'))
        data = {'asset': self.asset.id, 'snapshot_date': '2024-01-01', 'value': '200.00'}
        response = self.client.post('/api/fmv-snapshots/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════════════════
# T059: Tags CRUD & asset tag assignment API tests
# ═══════════════════════════════════════════════════════════════════════

class AssetTagAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_tag(self):
        data = {'name': 'Illiquid', 'color': '#EF4444'}
        response = self.client.post('/api/tags/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Illiquid')
        self.assertTrue(response.data['slug'])

    def test_list_tags(self):
        AssetTag.objects.create(name='Tag A', color='#111111')
        AssetTag.objects.create(name='Tag B', color='#222222')
        response = self.client.get('/api/tags/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_update_tag(self):
        tag = AssetTag.objects.create(name='Old Name', color='#333333')
        response = self.client.patch(f'/api/tags/{tag.id}/', {'name': 'New Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'New Name')

    def test_delete_tag(self):
        tag = AssetTag.objects.create(name='Delete Me', color='#444444')
        response = self.client.delete(f'/api/tags/{tag.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_set_asset_tags(self):
        asset = Asset.objects.create(name='Tagged Asset', asset_type='public_equity')
        tag1 = AssetTag.objects.create(name='Tag1', color='#111111')
        tag2 = AssetTag.objects.create(name='Tag2', color='#222222')
        response = self.client.post(
            f'/api/assets/{asset.id}/tags/',
            {'tag_ids': [tag1.id, tag2.id]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['tags']), 2)

    def test_replace_asset_tags(self):
        asset = Asset.objects.create(name='Replace Tag Asset', asset_type='cash')
        tag1 = AssetTag.objects.create(name='TagR1', color='#111111')
        tag2 = AssetTag.objects.create(name='TagR2', color='#222222')
        asset.tags.add(tag1)
        # Replace with only tag2
        response = self.client.post(
            f'/api/assets/{asset.id}/tags/',
            {'tag_ids': [tag2.id]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['tags']), 1)
        self.assertEqual(response.data['tags'][0]['name'], 'TagR2')


# ═══════════════════════════════════════════════════════════════════════
# T060: TWR and IRR calculation unit tests
# ═══════════════════════════════════════════════════════════════════════

class TWRCalculationTest(TestCase):
    def setUp(self):
        self.asset = Asset.objects.create(name='Perf Asset', asset_type='real_estate')

    def test_basic_twr(self):
        """Simple growth with no cash flows."""
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100000'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 7, 1), value=Decimal('110000'))
        result = calculate_twr(self.asset.id, datetime.date(2024, 1, 1), datetime.date(2024, 7, 1))
        self.assertIsNotNone(result['twr'])
        self.assertAlmostEqual(result['twr'], 10.0, places=1)  # 10% return

    def test_twr_with_distribution(self):
        """TWR should adjust for distributions."""
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100000'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 7, 1), value=Decimal('95000'))
        Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2024, 3, 15),
            total_amount=Decimal('10000'),
            distribution_type='regular',
        )
        result = calculate_twr(self.asset.id, datetime.date(2024, 1, 1), datetime.date(2024, 7, 1))
        self.assertIsNotNone(result['twr'])
        # After $10k distribution, $100k → $95k means $105k growth on $110k base
        self.assertGreater(result['twr'], 0)

    def test_twr_insufficient_data(self):
        """Should return None with fewer than 2 snapshots."""
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100000'))
        result = calculate_twr(self.asset.id, datetime.date(2024, 1, 1), datetime.date(2024, 7, 1))
        self.assertIsNone(result['twr'])

    def test_twr_no_snapshots(self):
        """Should return None with no snapshots."""
        result = calculate_twr(self.asset.id, datetime.date(2024, 1, 1), datetime.date(2024, 7, 1))
        self.assertIsNone(result['twr'])

    def test_twr_multi_period(self):
        """Geometric linking across multiple sub-periods."""
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100000'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 4, 1), value=Decimal('105000'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 7, 1), value=Decimal('115000'))
        result = calculate_twr(self.asset.id, datetime.date(2024, 1, 1), datetime.date(2024, 7, 1))
        self.assertIsNotNone(result['twr'])
        self.assertEqual(len(result['sub_periods']), 2)


class XIRRCalculationTest(TestCase):
    def test_simple_xirr(self):
        """Investment doubles in 1 year."""
        cfs = [
            (datetime.date(2023, 1, 1), -10000),
            (datetime.date(2024, 1, 1), 20000),
        ]
        irr = calculate_xirr(cfs)
        self.assertIsNotNone(irr)
        self.assertAlmostEqual(irr, 1.0, places=1)  # ~100% return

    def test_xirr_with_intermediate_flows(self):
        """Multiple cash flows."""
        cfs = [
            (datetime.date(2023, 1, 1), -10000),
            (datetime.date(2023, 7, 1), 2000),
            (datetime.date(2024, 1, 1), 12000),
        ]
        irr = calculate_xirr(cfs)
        self.assertIsNotNone(irr)
        self.assertGreater(irr, 0)

    def test_xirr_insufficient_data(self):
        """Should return None with < 2 cash flows."""
        cfs = [(datetime.date(2023, 1, 1), -10000)]
        irr = calculate_xirr(cfs)
        self.assertIsNone(irr)

    def test_xirr_all_same_sign(self):
        """Should return None when all flows are same sign."""
        cfs = [
            (datetime.date(2023, 1, 1), 10000),
            (datetime.date(2024, 1, 1), 20000),
        ]
        irr = calculate_xirr(cfs)
        self.assertIsNone(irr)

    def test_xirr_zero_return(self):
        """Get money back exactly."""
        cfs = [
            (datetime.date(2023, 1, 1), -10000),
            (datetime.date(2024, 1, 1), 10000),
        ]
        irr = calculate_xirr(cfs)
        self.assertIsNotNone(irr)
        self.assertAlmostEqual(irr, 0.0, places=1)


class PeriodResolverTest(TestCase):
    def test_ytd(self):
        start, end, label = resolve_period('ytd', datetime.date(2024, 6, 15))
        self.assertEqual(start, datetime.date(2024, 1, 1))
        self.assertEqual(end, datetime.date(2024, 6, 15))
        self.assertEqual(label, 'YTD')

    def test_1y(self):
        start, end, label = resolve_period('1y', datetime.date(2024, 6, 15))
        self.assertEqual(start, datetime.date(2024, 6, 15) - datetime.timedelta(days=365))
        self.assertEqual(end, datetime.date(2024, 6, 15))

    def test_since_inception(self):
        start, end, label = resolve_period('since_inception', datetime.date(2024, 6, 15))
        self.assertIsNone(start)
        self.assertEqual(label, 'Since Inception')

    def test_annualize_return(self):
        # 10% over 2 years → ~4.88% annualized
        result = annualize_return(0.10, 730)
        self.assertAlmostEqual(result, 0.0488, places=3)


class AssetIRRTest(TestCase):
    def setUp(self):
        self.asset = Asset.objects.create(name='IRR Asset', asset_type='public_equity')

    def test_basic_irr(self):
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2023, 1, 1), value=Decimal('100000'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('120000'))
        result = calculate_asset_irr(self.asset.id, datetime.date(2023, 1, 1), datetime.date(2024, 1, 1))
        self.assertIsNotNone(result['irr'])
        self.assertGreater(result['irr'], 0)

    def test_irr_insufficient_data(self):
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('100000'))
        result = calculate_asset_irr(self.asset.id, datetime.date(2024, 1, 1), datetime.date(2024, 7, 1))
        self.assertIsNone(result['irr'])


# ═══════════════════════════════════════════════════════════════════════
# T061: Performance endpoint API tests
# ═══════════════════════════════════════════════════════════════════════

class PerformanceAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.asset = Asset.objects.create(name='Perf API Asset', asset_type='real_estate')
        self.entity = Entity.objects.create(name='Perf Entity', entity_type='LLC')
        EntityAssetOwnership.objects.create(
            entity=self.entity, asset=self.asset,
            percentage=Decimal('100.0000'),
            effective_date=datetime.date(2023, 1, 1),
        )
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2023, 1, 1), value=Decimal('100000'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2023, 7, 1), value=Decimal('110000'))
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('120000'))

    def test_asset_performance_endpoint(self):
        response = self.client.get(f'/api/assets/{self.asset.id}/performance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('metrics', response.data)
        self.assertIn('fmv_series', response.data)

    def test_asset_performance_404(self):
        response = self.client.get('/api/assets/99999/performance/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_entity_performance_endpoint(self):
        response = self.client.get(f'/api/entities/{self.entity.id}/performance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('metrics', response.data)
        self.assertIn('assets', response.data)

    def test_entity_performance_404(self):
        response = self.client.get('/api/entities/99999/performance/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_performance_summary_endpoint(self):
        response = self.client.get('/api/performance/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_assets', response.data)
        self.assertIn('total_fmv', response.data)
        self.assertIn('by_asset_type', response.data)

    def test_asset_performance_with_calc_date(self):
        response = self.client.get(f'/api/assets/{self.asset.id}/performance/?calc_date=2024-01-01')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_asset_performance_invalid_date(self):
        response = self.client.get(f'/api/assets/{self.asset.id}/performance/?calc_date=not-a-date')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════════════════
# T063: Portfolio-by-class and dashboard net worth tests
# ═══════════════════════════════════════════════════════════════════════

class PortfolioByClassAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.asset1 = Asset.objects.create(name='Property A', asset_type='real_estate')
        self.asset2 = Asset.objects.create(name='Stock B', asset_type='public_equity')
        FMVSnapshot.objects.create(asset=self.asset1, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('1000000'))
        FMVSnapshot.objects.create(asset=self.asset2, snapshot_date=datetime.date(2024, 1, 1), value=Decimal('500000'))

    def test_portfolio_by_class(self):
        response = self.client.get('/api/reports/portfolio-by-class/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_fmv', response.data)
        self.assertIn('by_asset_type', response.data)
        self.assertEqual(len(response.data['by_asset_type']), 2)

    def test_portfolio_by_class_entity_filter(self):
        entity = Entity.objects.create(name='Filter Entity', entity_type='LLC')
        EntityAssetOwnership.objects.create(
            entity=entity, asset=self.asset1,
            percentage=Decimal('50.0000'),
            effective_date=datetime.date(2023, 1, 1),
        )
        response = self.client.get(f'/api/reports/portfolio-by-class/?entity_id={entity.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['by_asset_type']), 1)  # Only asset1 owned by entity


class DashboardNetWorthTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Net Worth Entity', entity_type='individual')
        self.asset = Asset.objects.create(name='NW Asset', asset_type='real_estate')
        EntityAssetOwnership.objects.create(
            entity=self.entity, asset=self.asset,
            percentage=Decimal('100.0000'),
            effective_date=datetime.date(2024, 1, 1),
        )
        FMVSnapshot.objects.create(asset=self.asset, snapshot_date=datetime.date(2024, 6, 1), value=Decimal('500000'))

    def test_dashboard_includes_net_worth(self):
        response = self.client.get('/api/reports/dashboard-summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('net_worth', response.data)
        nw = response.data['net_worth']
        self.assertIn('consolidated_net_worth', nw)
        self.assertIn('by_entity', nw)
        self.assertEqual(len(nw['by_entity']), 1)
        self.assertEqual(nw['by_entity'][0]['entity_name'], 'Net Worth Entity')
