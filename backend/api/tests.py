from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import datetime

from .models import Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation


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
            'asset_type': 'property',
            'address': '123 Main St, Springfield, IL',
        }
        response = self.client.post('/api/assets/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['asset_type'], 'property')

    def test_create_stock_asset(self):
        data = {
            'name': 'Apple Inc',
            'asset_type': 'stock',
            'ticker_symbol': 'AAPL',
        }
        response = self.client.post('/api/assets/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ticker_symbol'], 'AAPL')


class OwnershipAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.entity = Entity.objects.create(name='Investor A', entity_type='individual')
        self.asset = Asset.objects.create(name='Property X', asset_type='property')

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
        self.asset = Asset.objects.create(name='Property A', asset_type='property')

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
        self.asset = Asset.objects.create(name='Test Property', asset_type='property')
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
