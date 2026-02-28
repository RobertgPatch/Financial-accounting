"""
Plaid integration tests with mocked plaid-python client (T062).
"""
from unittest.mock import patch, MagicMock
from decimal import Decimal
import datetime

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from api.models import Asset, FMVSnapshot
from .models import PlaidItem, PlaidAccount


class PlaidCreateLinkTokenTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('plaid_integration.services.create_link_token')
    def test_create_link_token_success(self, mock_create):
        mock_create.return_value = {'link_token': 'link-sandbox-token', 'expiration': '2024-12-31T00:00:00Z'}
        response = self.client.post('/api/plaid/create-link-token/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('link_token', response.data)

    @patch('plaid_integration.services.create_link_token')
    def test_create_link_token_failure(self, mock_create):
        mock_create.side_effect = Exception('Plaid error')
        response = self.client.post('/api/plaid/create-link-token/')
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('error', response.data)


class PlaidExchangeTokenTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('plaid_integration.services.exchange_public_token')
    def test_exchange_token_success(self, mock_exchange):
        mock_exchange.return_value = {
            'item_id': 'item-sandbox-123',
            'access_token': 'access-sandbox-token',
        }
        data = {
            'public_token': 'public-sandbox-token',
            'institution': {'institution_id': 'ins_123', 'name': 'Test Bank'},
            'accounts': [
                {'id': 'acc_1', 'name': 'Checking', 'mask': '1234', 'type': 'depository', 'subtype': 'checking'},
            ],
        }
        response = self.client.post('/api/plaid/exchange-token/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('plaid_item_id', response.data)
        self.assertEqual(response.data['institution_name'], 'Test Bank')
        self.assertEqual(len(response.data['accounts']), 1)
        # Verify DB records
        self.assertEqual(PlaidItem.objects.count(), 1)
        self.assertEqual(PlaidAccount.objects.count(), 1)

    @patch('plaid_integration.services.exchange_public_token')
    def test_exchange_token_plaid_failure(self, mock_exchange):
        mock_exchange.side_effect = Exception('Exchange failed')
        data = {'public_token': 'bad-token', 'institution': {}, 'accounts': []}
        response = self.client.post('/api/plaid/exchange-token/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_exchange_token_missing_public_token(self):
        data = {'institution': {}, 'accounts': []}
        response = self.client.post('/api/plaid/exchange-token/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PlaidSyncBalancesTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.plaid_item = PlaidItem.objects.create(
            item_id='item-123',
            access_token='access-123',
            institution_name='Test Bank',
            status='active',
        )
        self.asset = Asset.objects.create(name='Mapped Asset', asset_type='cash')
        self.plaid_account = PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='acc_123',
            name='Checking',
            mask='1234',
            type='depository',
            subtype='checking',
            asset=self.asset,
        )

    @patch('plaid_integration.services.get_balances')
    def test_sync_balances_success(self, mock_balances):
        mock_balances.return_value = [
            {'account_id': 'acc_123', 'current_balance': 50000.00},
        ]
        response = self.client.post(f'/api/plaid/items/{self.plaid_item.id}/sync/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.plaid_account.refresh_from_db()
        self.assertEqual(self.plaid_account.current_balance, Decimal('50000.00'))

    @patch('plaid_integration.services.get_balances')
    def test_sync_creates_fmv_snapshot(self, mock_balances):
        mock_balances.return_value = [
            {'account_id': 'acc_123', 'current_balance': 75000.00},
        ]
        self.client.post(f'/api/plaid/items/{self.plaid_item.id}/sync/')
        # Should create an FMV snapshot for the mapped asset
        snap = FMVSnapshot.objects.filter(asset=self.asset).first()
        self.assertIsNotNone(snap)
        self.assertEqual(snap.value, Decimal('75000.00'))
        self.assertEqual(snap.source, 'plaid')

    @patch('plaid_integration.services.get_balances')
    def test_sync_plaid_failure(self, mock_balances):
        mock_balances.side_effect = Exception('API failure')
        response = self.client.post(f'/api/plaid/items/{self.plaid_item.id}/sync/')
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.plaid_item.refresh_from_db()
        self.assertEqual(self.plaid_item.status, 'error')

    def test_sync_item_not_found(self):
        response = self.client.post('/api/plaid/items/99999/sync/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PlaidMapAssetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.plaid_item = PlaidItem.objects.create(
            item_id='item-map',
            access_token='access-map',
            institution_name='Map Bank',
            status='active',
        )
        self.plaid_account = PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='acc_map',
            name='Savings',
            mask='5678',
            type='depository',
            subtype='savings',
        )
        self.asset = Asset.objects.create(name='Map Target', asset_type='cash')

    def test_map_asset_success(self):
        response = self.client.patch(
            f'/api/plaid/accounts/{self.plaid_account.id}/map-asset/',
            {'asset_id': self.asset.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.plaid_account.refresh_from_db()
        self.assertEqual(self.plaid_account.asset_id, self.asset.id)

    def test_map_asset_already_mapped(self):
        other_account = PlaidAccount.objects.create(
            plaid_item=self.plaid_item,
            account_id='acc_other',
            name='Other',
            mask='9999',
            type='depository',
            asset=self.asset,
        )
        response = self.client.patch(
            f'/api/plaid/accounts/{self.plaid_account.id}/map-asset/',
            {'asset_id': self.asset.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_map_asset_not_found(self):
        response = self.client.patch(
            '/api/plaid/accounts/99999/map-asset/',
            {'asset_id': self.asset.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PlaidListItemsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        PlaidItem.objects.create(
            item_id='item-list-1', access_token='at-1',
            institution_name='Bank A', status='active',
        )
        PlaidItem.objects.create(
            item_id='item-list-2', access_token='at-2',
            institution_name='Bank B', status='active',
        )

    def test_list_items(self):
        response = self.client.get('/api/plaid/items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_item_accounts(self):
        item = PlaidItem.objects.first()
        PlaidAccount.objects.create(
            plaid_item=item, account_id='acc-la-1',
            name='Checking', mask='0001', type='depository',
        )
        response = self.client.get(f'/api/plaid/items/{item.id}/accounts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_item_accounts_not_found(self):
        response = self.client.get('/api/plaid/items/99999/accounts/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
