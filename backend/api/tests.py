from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import datetime

from .models import Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation, Budget, BudgetLineItem, AssetTag, FMVSnapshot, Commitment, CapitalCall
from .performance import calculate_twr, calculate_xirr, calculate_asset_irr, resolve_period, annualize_return, compute_entity_xirr
from .reports import generate_portfolio_summary, generate_asset_class_summary, generate_investment_performance


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


# ═══════════════════════════════════════════════════════════════════════
# FMV Report Tests (Feature 002: FMV Auto-Reporting)
# ═══════════════════════════════════════════════════════════════════════

from plaid_integration.models import PlaidItem, PlaidAccount
from api.reports import generate_fmv_report, PLAID_TYPE_MAP, ASSET_TYPE_LABELS


class FMVReportTests(TestCase):
    """T006: Core FMV report generation tests."""

    def setUp(self):
        self.client = APIClient()
        # Create a Plaid item (institution)
        self.plaid_item = PlaidItem.objects.create(
            item_id='test_item_1',
            access_token='test_token_1',
            institution_name='Chase',
            status='active',
        )
        # Create Plaid accounts
        self.checking = PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='checking_1',
            name='Chase Checking',
            mask='1234',
            type='depository',
            subtype='checking',
            current_balance=Decimal('45000.00'),
        )
        self.investment = PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='invest_1',
            name='Fidelity 401k',
            mask='5678',
            type='investment',
            subtype='401k',
            current_balance=Decimal('185000.00'),
        )

    def test_basic_report_generation(self):
        """Test basic FMV report with Plaid accounts returns correct total and items."""
        report = generate_fmv_report()
        self.assertEqual(report['total_fmv'], '230000.00')
        self.assertEqual(report['item_count'], 2)
        self.assertEqual(len(report['items']), 2)
        # Check items include both accounts
        names = [item['name'] for item in report['items']]
        self.assertIn('Chase Checking', names)
        self.assertIn('Fidelity 401k', names)

    def test_plaid_type_map_categorization(self):
        """Test PLAID_TYPE_MAP categorizes types correctly."""
        self.assertEqual(PLAID_TYPE_MAP['depository'], 'cash')
        self.assertEqual(PLAID_TYPE_MAP['investment'], 'public_equity')
        self.assertEqual(PLAID_TYPE_MAP['loan'], 'fixed_income')
        self.assertEqual(PLAID_TYPE_MAP['credit'], 'cash')
        # Verify report uses correct type mapping
        report = generate_fmv_report()
        checking_item = next(i for i in report['items'] if i['name'] == 'Chase Checking')
        invest_item = next(i for i in report['items'] if i['name'] == 'Fidelity 401k')
        self.assertEqual(checking_item['asset_type'], 'cash')
        self.assertEqual(invest_item['asset_type'], 'public_equity')

    def test_double_count_prevention(self):
        """Test mapped Plaid account excludes manual asset's FMV snapshot."""
        # Create a manual asset and map a Plaid account to it
        asset = Asset.objects.create(name='My Investment', asset_type='public_equity')
        FMVSnapshot.objects.create(
            asset=asset, snapshot_date=datetime.date(2026, 2, 15),
            value=Decimal('200000.00'), source='manual',
        )
        # Map the investment Plaid account to this asset
        self.investment.asset = asset
        self.investment.save()

        report = generate_fmv_report()
        # The manual asset should NOT appear (Plaid account replaces it)
        manual_items = [i for i in report['items'] if i['source'] == 'manual']
        self.assertEqual(len(manual_items), 0)
        # Plaid account should use the mapped asset's type
        invest_item = next(i for i in report['items'] if i['name'] == 'Fidelity 401k')
        self.assertEqual(invest_item['asset_type'], 'public_equity')
        # Total should be Plaid balances only (45000 + 185000)
        self.assertEqual(report['total_fmv'], '230000.00')

    def test_empty_state(self):
        """Test empty state returns zero total and empty items."""
        PlaidAccount.objects.all().delete()
        report = generate_fmv_report()
        self.assertEqual(report['total_fmv'], '0.00')
        self.assertEqual(report['item_count'], 0)
        self.assertEqual(report['items'], [])
        self.assertEqual(report['by_type'], [])

    def test_negative_plaid_balance(self):
        """Test negative Plaid balance (credit card) reduces total."""
        PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='credit_1',
            name='Visa Credit Card',
            mask='9012',
            type='credit',
            subtype='credit card',
            current_balance=Decimal('-3500.00'),
        )
        report = generate_fmv_report()
        # 45000 + 185000 + (-3500) = 226500
        self.assertEqual(report['total_fmv'], '226500.00')
        credit_item = next(i for i in report['items'] if i['name'] == 'Visa Credit Card')
        self.assertEqual(credit_item['value'], '-3500.00')
        self.assertEqual(credit_item['asset_type'], 'cash')

    def test_plaid_null_balance_needs_sync(self):
        """Test Plaid account with current_balance=None appears with value 0 and needs_sync."""
        PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='unsynced_1',
            name='Unsynced Account',
            type='depository',
            current_balance=None,
        )
        report = generate_fmv_report()
        unsynced = next(i for i in report['items'] if i['name'] == 'Unsynced Account')
        self.assertEqual(unsynced['value'], '0.00')
        self.assertTrue(unsynced['needs_sync'])

    def test_manual_asset_included(self):
        """Test manual asset with FMV snapshot is included in report."""
        asset = Asset.objects.create(name='Beach House', asset_type='real_estate')
        FMVSnapshot.objects.create(
            asset=asset, snapshot_date=datetime.date(2026, 2, 15),
            value=Decimal('500000.00'), source='manual',
        )
        report = generate_fmv_report()
        self.assertEqual(report['item_count'], 3)
        manual = next(i for i in report['items'] if i['name'] == 'Beach House')
        self.assertEqual(manual['source'], 'manual')
        self.assertEqual(manual['value'], '500000.00')
        self.assertEqual(manual['asset_type'], 'real_estate')

    def test_manual_asset_without_snapshot_excluded(self):
        """Test manual asset without FMV snapshot is NOT included."""
        Asset.objects.create(name='No Snapshot Asset', asset_type='other')
        report = generate_fmv_report()
        names = [i['name'] for i in report['items']]
        self.assertNotIn('No Snapshot Asset', names)


class FMVReportAPIEndpointTests(TestCase):
    """T008: FMV API endpoint tests."""

    def setUp(self):
        self.client = APIClient()
        self.plaid_item = PlaidItem.objects.create(
            item_id='api_test_item',
            access_token='api_test_token',
            institution_name='Test Bank',
            status='active',
        )
        PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='api_checking_1',
            name='Test Checking',
            mask='1111',
            type='depository',
            subtype='checking',
            current_balance=Decimal('10000.00'),
        )

    def test_fmv_generate_endpoint_returns_200(self):
        """Test POST /api/reports/fmv/generate/ returns 200 with correct shape."""
        response = self.client.post('/api/reports/fmv/generate/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_fmv', response.data)
        self.assertIn('item_count', response.data)
        self.assertIn('filters', response.data)
        self.assertIn('by_type', response.data)
        self.assertIn('items', response.data)

    def test_plaid_accounts_auto_included(self):
        """Test Plaid accounts are auto-included without any mapping."""
        response = self.client.post('/api/reports/fmv/generate/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['item_count'], 1)
        self.assertEqual(response.data['items'][0]['source'], 'plaid')

    def test_needs_sync_flag(self):
        """Test needs_sync is True when current_balance is None."""
        PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='unsynced_api',
            name='Unsynced API Account',
            type='depository',
            current_balance=None,
        )
        response = self.client.post('/api/reports/fmv/generate/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        unsynced = next(i for i in response.data['items'] if i['name'] == 'Unsynced API Account')
        self.assertTrue(unsynced['needs_sync'])
        self.assertEqual(unsynced['value'], '0.00')


class FMVReportTypeFilterTests(TestCase):
    """T012: Type filter tests for FMV report."""

    def setUp(self):
        self.plaid_item = PlaidItem.objects.create(
            item_id='filter_test_item',
            access_token='filter_test_token',
            institution_name='Filter Bank',
            status='active',
        )
        PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='filter_checking',
            name='Filter Checking',
            type='depository',
            current_balance=Decimal('5000.00'),
        )
        PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='filter_invest',
            name='Filter Investment',
            type='investment',
            current_balance=Decimal('20000.00'),
        )

    def test_single_type_filter(self):
        """Test type_filters=['cash'] returns only cash-typed items."""
        report = generate_fmv_report(type_filters=['cash'])
        self.assertEqual(report['item_count'], 1)
        self.assertEqual(report['items'][0]['asset_type'], 'cash')

    def test_multiple_type_filters(self):
        """Test multiple filters returns combined results."""
        report = generate_fmv_report(type_filters=['cash', 'public_equity'])
        self.assertEqual(report['item_count'], 2)
        types = {i['asset_type'] for i in report['items']}
        self.assertEqual(types, {'cash', 'public_equity'})

    def test_filter_no_matching_items(self):
        """Test filter with no matching items returns empty."""
        report = generate_fmv_report(type_filters=['real_estate'])
        self.assertEqual(report['total_fmv'], '0.00')
        self.assertEqual(report['item_count'], 0)
        self.assertEqual(report['items'], [])

    def test_no_filter_returns_all(self):
        """Test filter=None returns all items."""
        report = generate_fmv_report(type_filters=None)
        self.assertEqual(report['item_count'], 2)


class FMVReportEntityFilterTests(TestCase):
    """T014: Entity filter and manual asset tests for FMV report."""

    def setUp(self):
        self.entity = Entity.objects.create(name='Test Trust', entity_type='trust')
        self.other_entity = Entity.objects.create(name='Other LLC', entity_type='LLC')

        # Manual asset owned by test entity
        self.owned_asset = Asset.objects.create(name='Owned Property', asset_type='real_estate')
        FMVSnapshot.objects.create(
            asset=self.owned_asset, snapshot_date=datetime.date(2026, 1, 15),
            value=Decimal('300000.00'), source='manual',
        )
        EntityAssetOwnership.objects.create(
            entity=self.entity, asset=self.owned_asset,
            percentage=Decimal('100.0000'),
            effective_date=datetime.date(2025, 1, 1),
        )

        # Manual asset owned by other entity
        self.other_asset = Asset.objects.create(name='Other Property', asset_type='real_estate')
        FMVSnapshot.objects.create(
            asset=self.other_asset, snapshot_date=datetime.date(2026, 1, 15),
            value=Decimal('200000.00'), source='manual',
        )
        EntityAssetOwnership.objects.create(
            entity=self.other_entity, asset=self.other_asset,
            percentage=Decimal('100.0000'),
            effective_date=datetime.date(2025, 1, 1),
        )

        # Plaid setup
        self.plaid_item = PlaidItem.objects.create(
            item_id='entity_test_item',
            access_token='entity_test_token',
            institution_name='Entity Bank',
            status='active',
        )

        # Unmapped Plaid account
        self.unmapped_plaid = PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='entity_unmapped',
            name='Unmapped Checking',
            type='depository',
            current_balance=Decimal('10000.00'),
        )

        # Plaid account mapped to owned asset
        self.mapped_plaid = PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='entity_mapped',
            name='Mapped Account',
            type='investment',
            current_balance=Decimal('50000.00'),
            asset=self.owned_asset,
        )

    def test_entity_filter_excludes_unmapped_plaid(self):
        """Test entity filter excludes unmapped Plaid accounts."""
        report = generate_fmv_report(entity_ids=[self.entity.id])
        names = [i['name'] for i in report['items']]
        self.assertNotIn('Unmapped Checking', names)

    def test_entity_filter_includes_owned_manual_assets(self):
        """Test entity filter includes manual assets with ownership records."""
        # Note: self.owned_asset is mapped to Plaid, so it won't appear as manual
        # Let's create an unmapped manual asset owned by entity
        unmapped_manual = Asset.objects.create(name='Unmapped Manual', asset_type='cash')
        FMVSnapshot.objects.create(
            asset=unmapped_manual, snapshot_date=datetime.date(2026, 1, 15),
            value=Decimal('25000.00'), source='manual',
        )
        EntityAssetOwnership.objects.create(
            entity=self.entity, asset=unmapped_manual,
            percentage=Decimal('100.0000'),
            effective_date=datetime.date(2025, 1, 1),
        )
        report = generate_fmv_report(entity_ids=[self.entity.id])
        names = [i['name'] for i in report['items']]
        self.assertIn('Unmapped Manual', names)

    def test_entity_filter_includes_mapped_plaid_for_owned_asset(self):
        """Test entity filter includes Plaid accounts mapped to assets owned by entity."""
        report = generate_fmv_report(entity_ids=[self.entity.id])
        names = [i['name'] for i in report['items']]
        self.assertIn('Mapped Account', names)

    def test_manual_asset_without_snapshot_excluded(self):
        """Test manual asset without FMV snapshot is excluded."""
        Asset.objects.create(name='No Snapshot', asset_type='other')
        report = generate_fmv_report()
        names = [i['name'] for i in report['items']]
        self.assertNotIn('No Snapshot', names)

    def test_manual_asset_source_correct(self):
        """Test manual asset with FMV snapshot appears with correct source."""
        # Create an unmapped manual asset
        standalone = Asset.objects.create(name='Standalone Asset', asset_type='crypto')
        FMVSnapshot.objects.create(
            asset=standalone, snapshot_date=datetime.date(2026, 2, 1),
            value=Decimal('15000.00'), source='manual',
        )
        report = generate_fmv_report()
        manual = next(i for i in report['items'] if i['name'] == 'Standalone Asset')
        self.assertEqual(manual['source'], 'manual')

    def test_double_count_prevention_with_entity_filter(self):
        """Test mapped asset's FMV snapshot excluded when entity filter active."""
        report = generate_fmv_report(entity_ids=[self.entity.id])
        # Owned Property is mapped to a Plaid account, so it shouldn't appear as manual
        manual_items = [i for i in report['items'] if i['source'] == 'manual' and i['name'] == 'Owned Property']
        self.assertEqual(len(manual_items), 0)
        # The mapped Plaid account should be there
        plaid_items = [i for i in report['items'] if i['name'] == 'Mapped Account']
        self.assertEqual(len(plaid_items), 1)


class DistributionReportNoFMVTest(TestCase):
    """T010: Distribution report no-FMV assertion."""

    def test_distribution_report_has_no_fmv_keys(self):
        """Test generate_distribution_report() does NOT contain FMV keys."""
        from api.reports import generate_distribution_report
        report = generate_distribution_report()
        fmv_keys = {'total_fmv', 'fmv', 'net_worth', 'by_type'}
        for key in fmv_keys:
            self.assertNotIn(key, report, f"Distribution report should not contain '{key}'")
        # Confirm expected keys are present
        expected_keys = {'period', 'summary', 'by_entity', 'by_asset', 'detail',
                        'budget_comparison', 'yoy_comparison', 'retained_earnings'}
        for key in expected_keys:
            self.assertIn(key, report, f"Distribution report missing expected key '{key}'")


class FMVExportEndpointTests(TestCase):
    """T019: FMV export endpoint tests."""

    def setUp(self):
        self.client = APIClient()
        self.plaid_item = PlaidItem.objects.create(
            item_id='export_test_item',
            access_token='export_test_token',
            institution_name='Export Bank',
            status='active',
        )
        PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='export_checking',
            name='Export Checking',
            mask='4444',
            type='depository',
            current_balance=Decimal('15000.00'),
        )

    def test_fmv_export_returns_xlsx(self):
        """Test POST /api/reports/fmv/export/ returns 200 with xlsx content type."""
        response = self.client.post('/api/reports/fmv/export/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_fmv_export_content_disposition(self):
        """Test Content-Disposition header contains fmv_report_ and .xlsx."""
        response = self.client.post('/api/reports/fmv/export/', {}, format='json')
        self.assertIn('fmv_report_', response['Content-Disposition'])
        self.assertIn('.xlsx', response['Content-Disposition'])

    def test_fmv_export_with_type_filters(self):
        """Test export with type_filters produces valid response."""
        response = self.client.post(
            '/api/reports/fmv/export/',
            {'type_filters': ['cash']},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


# ===========================================================================
# Portfolio Tracker Tests
# ===========================================================================

class CommitmentAPITest(TestCase):
    """Tests for Commitment CRUD endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Test Entity', entity_type='LLC')
        self.asset = Asset.objects.create(name='PE Fund I', asset_type='private_equity')

    def test_create_commitment(self):
        data = {
            'entity': self.entity.id,
            'asset': self.asset.id,
            'commitment_date': '2024-01-15',
            'original_amount': '1000000.00',
        }
        response = self.client.post('/api/commitments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['original_amount'], '1000000.00')
        self.assertEqual(response.data['entity_name'], 'Test Entity')
        self.assertEqual(response.data['asset_name'], 'PE Fund I')
        self.assertEqual(response.data['paid_in'], '0.00')
        self.assertEqual(response.data['pct_called'], '0.00')
        self.assertEqual(response.data['unfunded'], '1000000.00')
        self.assertEqual(response.data['call_count'], 0)

    def test_unique_constraint(self):
        Commitment.objects.create(
            entity=self.entity,
            asset=self.asset,
            commitment_date='2024-01-01',
            original_amount=Decimal('500000'),
        )
        data = {
            'entity': self.entity.id,
            'asset': self.asset.id,
            'commitment_date': '2024-06-01',
            'original_amount': '250000.00',
        }
        response = self.client.post('/api/commitments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_commitments_filter_entity(self):
        Commitment.objects.create(
            entity=self.entity, asset=self.asset,
            commitment_date='2024-01-01', original_amount=Decimal('100000'),
        )
        response = self.client.get(f'/api/commitments/?entity={self.entity.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_update_commitment(self):
        c = Commitment.objects.create(
            entity=self.entity, asset=self.asset,
            commitment_date='2024-01-01', original_amount=Decimal('100000'),
        )
        response = self.client.patch(
            f'/api/commitments/{c.id}/',
            {'original_amount': '200000.00'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['original_amount'], '200000.00')

    def test_delete_commitment(self):
        c = Commitment.objects.create(
            entity=self.entity, asset=self.asset,
            commitment_date='2024-01-01', original_amount=Decimal('100000'),
        )
        response = self.client.delete(f'/api/commitments/{c.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CapitalCallAPITest(TestCase):
    """Tests for CapitalCall CRUD endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Entity A', entity_type='LLC')
        self.asset = Asset.objects.create(name='Fund A', asset_type='private_equity')
        self.commitment = Commitment.objects.create(
            entity=self.entity, asset=self.asset,
            commitment_date='2024-01-01', original_amount=Decimal('1000000'),
        )

    def test_create_capital_call(self):
        data = {
            'commitment': self.commitment.id,
            'call_date': '2024-06-15',
            'amount': '250000.00',
        }
        response = self.client.post('/api/capital-calls/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['amount'], '250000.00')
        self.assertIn('Entity A', response.data['commitment_display'])

    def test_list_capital_calls_filter_commitment(self):
        CapitalCall.objects.create(
            commitment=self.commitment, call_date='2024-06-15', amount=Decimal('200000'),
        )
        response = self.client.get(f'/api/capital-calls/?commitment={self.commitment.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_commitment_computed_fields_after_call(self):
        """After a capital call, commitment's computed fields update correctly."""
        CapitalCall.objects.create(
            commitment=self.commitment, call_date='2024-06-15', amount=Decimal('600000'),
        )
        response = self.client.get(f'/api/commitments/{self.commitment.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['paid_in'], '600000.00')
        self.assertEqual(response.data['pct_called'], '60.00')
        self.assertEqual(response.data['unfunded'], '400000.00')
        self.assertEqual(response.data['call_count'], 1)

    def test_full_capital_call(self):
        """100% called => unfunded = 0."""
        CapitalCall.objects.create(
            commitment=self.commitment, call_date='2024-06-15', amount=Decimal('1000000'),
        )
        response = self.client.get(f'/api/commitments/{self.commitment.id}/')
        self.assertEqual(response.data['pct_called'], '100.00')
        self.assertEqual(response.data['unfunded'], '0.00')


class PortfolioSummaryAPITest(TestCase):
    """Tests for POST /api/portfolio/summary/."""

    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Entity One', entity_type='LLC')
        self.asset = Asset.objects.create(name='PE Fund Alpha', asset_type='private_equity')
        EntityAssetOwnership.objects.create(
            entity=self.entity, asset=self.asset, percentage=Decimal('100'),
            effective_date=datetime.date(2023, 1, 1),
        )
        self.commitment = Commitment.objects.create(
            entity=self.entity, asset=self.asset,
            commitment_date='2023-01-01', original_amount=Decimal('1000000'),
        )
        CapitalCall.objects.create(
            commitment=self.commitment, call_date='2023-06-15', amount=Decimal('1000000'),
        )
        # Distribution
        dist = Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2024, 6, 15),
            total_amount=Decimal('2000000'),
        )
        DistributionAllocation.objects.create(
            distribution=dist, entity=self.entity, amount=Decimal('2000000'),
            percentage=Decimal('100.0000'),
        )

    def test_summary_returns_entity_data(self):
        response = self.client.post('/api/portfolio/summary/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn('entities', data)
        self.assertIn('all_entities', data)
        self.assertGreaterEqual(len(data['entities']), 1)

        ent = data['entities'][0]
        self.assertEqual(ent['entity_name'], 'Entity One')
        self.assertEqual(ent['original_commitment'], '1000000.00')
        self.assertEqual(ent['paid_in'], '1000000.00')
        self.assertEqual(ent['distributions'], '2000000.00')
        # DPI = 2M / 1M = 2.00
        self.assertEqual(ent['dpi'], '2.00')

    def test_summary_with_entity_filter(self):
        response = self.client.post(
            '/api/portfolio/summary/',
            {'entity_ids': str(self.entity.id)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['entities']), 1)

    def test_summary_empty_entity(self):
        """Entity with no commitments shows zero values and null ratios."""
        empty_entity = Entity.objects.create(name='Empty Entity', entity_type='trust')
        response = self.client.post(
            '/api/portfolio/summary/',
            {'entity_ids': str(empty_entity.id)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ent = response.data['entities'][0]
        self.assertEqual(ent['original_commitment'], '0.00')
        self.assertIsNone(ent['pct_called'])  # div by zero
        self.assertIsNone(ent['dpi'])
        self.assertIsNone(ent['rvpi'])
        self.assertIsNone(ent['tvpi'])
        self.assertIsNone(ent['irr'])


class PortfolioSummaryExportTest(TestCase):
    """Test POST /api/portfolio/summary/export/."""

    def setUp(self):
        self.client = APIClient()

    def test_export_returns_xlsx(self):
        response = self.client.post('/api/portfolio/summary/export/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('.xlsx', response['Content-Disposition'])


class AssetClassSummaryAPITest(TestCase):
    """Tests for POST /api/portfolio/asset-class-summary/."""

    def setUp(self):
        self.client = APIClient()
        self.asset_re = Asset.objects.create(name='Beach House', asset_type='real_estate')
        FMVSnapshot.objects.create(
            asset=self.asset_re,
            snapshot_date=datetime.date.today(),
            value=Decimal('500000'),
        )
        self.asset_cash = Asset.objects.create(name='Savings', asset_type='cash')
        FMVSnapshot.objects.create(
            asset=self.asset_cash,
            snapshot_date=datetime.date.today(),
            value=Decimal('200000'),
        )

    def test_summary_returns_classes(self):
        response = self.client.post('/api/portfolio/asset-class-summary/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn('rows', data)
        self.assertIn('all_classes', data)
        self.assertIn('as_of_date', data)

    def test_summary_type_filter(self):
        response = self.client.post(
            '/api/portfolio/asset-class-summary/',
            {'type_filters': ['real_estate']},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Filters should be echoed back
        self.assertEqual(response.data['filters']['type_filters'], ['real_estate'])

    def test_empty_portfolio(self):
        Asset.objects.all().delete()
        FMVSnapshot.objects.all().delete()
        response = self.client.post('/api/portfolio/asset-class-summary/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('all_classes', response.data)
        self.assertEqual(response.data['all_classes']['paid_in'], '0.00')


class AssetClassSummaryExportTest(TestCase):
    """Test POST /api/portfolio/asset-class-summary/export/."""

    def setUp(self):
        self.client = APIClient()

    def test_export_returns_xlsx(self):
        response = self.client.post('/api/portfolio/asset-class-summary/export/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


class InvestmentPerformanceAPITest(TestCase):
    """Tests for POST /api/portfolio/performance/."""

    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Perf Entity', entity_type='LLC')
        self.asset = Asset.objects.create(name='PE Fund Beta', asset_type='private_equity')
        EntityAssetOwnership.objects.create(
            entity=self.entity, asset=self.asset, percentage=Decimal('100'),
            effective_date=datetime.date(2023, 1, 1),
        )
        self.commitment = Commitment.objects.create(
            entity=self.entity, asset=self.asset,
            commitment_date='2023-01-01', original_amount=Decimal('1000000'),
        )
        CapitalCall.objects.create(
            commitment=self.commitment, call_date='2023-03-01', amount=Decimal('1000000'),
        )
        dist = Distribution.objects.create(
            asset=self.asset,
            distribution_date=datetime.date(2024, 3, 1),
            total_amount=Decimal('2000000'),
        )
        DistributionAllocation.objects.create(
            distribution=dist, entity=self.entity, amount=Decimal('2000000'),
            percentage=Decimal('100.0000'),
        )

    def test_performance_returns_investments(self):
        response = self.client.post('/api/portfolio/performance/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn('investments', data)
        self.assertIn('entity_totals', data)
        self.assertGreaterEqual(len(data['investments']), 1)
        inv = data['investments'][0]
        self.assertEqual(inv['asset_name'], 'PE Fund Beta')
        self.assertEqual(inv['paid_in'], '1000000.00')
        self.assertEqual(inv['distributions'], '2000000.00')
        self.assertEqual(inv['dpi'], '2.00')

    def test_performance_entity_filter(self):
        response = self.client.post(
            '/api/portfolio/performance/',
            {'entity_ids': str(self.entity.id)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['investments']), 1)

    def test_performance_no_data(self):
        """No commitments → empty investments list."""
        empty_entity = Entity.objects.create(name='Empty', entity_type='trust')
        response = self.client.post(
            '/api/portfolio/performance/',
            {'entity_ids': str(empty_entity.id)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['investments']), 0)


class InvestmentPerformanceExportTest(TestCase):
    """Test POST /api/portfolio/performance/export/."""

    def setUp(self):
        self.client = APIClient()

    def test_export_returns_xlsx(self):
        response = self.client.post('/api/portfolio/performance/export/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


class PortfolioEdgeCaseTest(TestCase):
    """Edge case tests for portfolio metrics."""

    def test_zero_commitment_pct_called_null(self):
        """When original_commitment is $0, pct_called should be None (displayed as '—')."""
        entity = Entity.objects.create(name='Zero Commitment', entity_type='LLC')
        asset = Asset.objects.create(name='Fund Z', asset_type='private_equity')
        EntityAssetOwnership.objects.create(
            entity=entity, asset=asset, percentage=Decimal('100'),
            effective_date=datetime.date(2024, 1, 1),
        )
        Commitment.objects.create(
            entity=entity, asset=asset,
            commitment_date='2024-01-01', original_amount=Decimal('0'),
        )
        report = generate_portfolio_summary(entity_ids=[entity.id])
        ent = report['entities'][0]
        self.assertEqual(ent['original_commitment'], '0.00')
        self.assertIsNone(ent['pct_called'])
        self.assertEqual(ent['unfunded_commitment'], '0.00')

    def test_dpi_greater_than_one(self):
        """Distributions exceeding paid-in → DPI > 1.0 is valid."""
        entity = Entity.objects.create(name='High DPI', entity_type='LLC')
        asset = Asset.objects.create(name='Great Fund', asset_type='private_equity')
        EntityAssetOwnership.objects.create(
            entity=entity, asset=asset, percentage=Decimal('100'),
            effective_date=datetime.date(2023, 1, 1),
        )
        commitment = Commitment.objects.create(
            entity=entity, asset=asset,
            commitment_date='2023-01-01', original_amount=Decimal('100000'),
        )
        CapitalCall.objects.create(
            commitment=commitment, call_date='2023-03-01', amount=Decimal('100000'),
        )
        dist = Distribution.objects.create(
            asset=asset,
            distribution_date=datetime.date(2024, 6, 1),
            total_amount=Decimal('500000'),
        )
        DistributionAllocation.objects.create(
            distribution=dist, entity=entity, amount=Decimal('500000'),
            percentage=Decimal('100.0000'),
        )
        report = generate_portfolio_summary(entity_ids=[entity.id])
        ent = report['entities'][0]
        self.assertEqual(ent['dpi'], '5.00')
        self.assertEqual(ent['tvpi'], '5.00')

    def test_zero_paid_in_null_ratios(self):
        """With zero paid-in, DPI/RVPI/TVPI should be None."""
        entity = Entity.objects.create(name='No Calls', entity_type='LLC')
        asset = Asset.objects.create(name='Future Fund', asset_type='private_equity')
        EntityAssetOwnership.objects.create(
            entity=entity, asset=asset, percentage=Decimal('100'),
            effective_date=datetime.date(2024, 1, 1),
        )
        Commitment.objects.create(
            entity=entity, asset=asset,
            commitment_date='2024-01-01', original_amount=Decimal('500000'),
        )
        # No capital calls
        report = generate_portfolio_summary(entity_ids=[entity.id])
        ent = report['entities'][0]
        self.assertEqual(ent['paid_in'], '0.00')
        self.assertIsNone(ent['dpi'])
        self.assertIsNone(ent['rvpi'])
        self.assertIsNone(ent['tvpi'])
