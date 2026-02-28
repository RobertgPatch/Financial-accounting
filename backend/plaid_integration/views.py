import logging
from decimal import Decimal
from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.models import Asset, FMVSnapshot
from .models import PlaidItem, PlaidAccount
from .serializers import (
    PlaidItemSerializer, PlaidAccountSerializer,
    ExchangeTokenSerializer, MapAssetSerializer,
)
from . import services

logger = logging.getLogger(__name__)


@api_view(['POST'])
def create_link_token(request):
    """Create a Plaid Link token for the frontend."""
    from django.conf import settings as django_settings
    if not getattr(django_settings, 'PLAID_CLIENT_ID', '') or not getattr(django_settings, 'PLAID_SECRET', ''):
        return Response(
            {'error': 'Plaid is not configured. Set PLAID_CLIENT_ID and PLAID_SECRET environment variables.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
    try:
        result = services.create_link_token()
        return Response(result)
    except Exception as e:
        logger.error(f"Failed to create link token: {e}")
        return Response(
            {'error': 'Failed to connect to Plaid. Please try again.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(['POST'])
def exchange_token(request):
    """Exchange a public token for an access token after Plaid Link completes."""
    serializer = ExchangeTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        result = services.exchange_public_token(data['public_token'])
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return Response(
            {'error': 'Failed to exchange token with Plaid.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    institution = data.get('institution', {})
    accounts_data = data.get('accounts', [])

    with transaction.atomic():
        plaid_item = PlaidItem.objects.create(
            item_id=result['item_id'],
            access_token=result['access_token'],
            institution_id=institution.get('institution_id', ''),
            institution_name=institution.get('name', ''),
            status='active',
        )

        created_accounts = []
        for acct in accounts_data:
            pa = PlaidAccount.objects.create(
                plaid_item=plaid_item,
                account_id=acct.get('id', ''),
                name=acct.get('name', ''),
                mask=acct.get('mask', ''),
                type=acct.get('type', ''),
                subtype=acct.get('subtype', ''),
            )
            created_accounts.append(pa)

    return Response({
        'plaid_item_id': plaid_item.id,
        'institution_name': plaid_item.institution_name,
        'accounts': PlaidAccountSerializer(created_accounts, many=True).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def list_items(request):
    """List all linked Plaid institutions."""
    items = PlaidItem.objects.all()
    serializer = PlaidItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def list_item_accounts(request, item_id):
    """List accounts for a linked institution."""
    try:
        plaid_item = PlaidItem.objects.get(pk=item_id)
    except PlaidItem.DoesNotExist:
        return Response({'error': 'Plaid item not found'}, status=status.HTTP_404_NOT_FOUND)

    accounts = plaid_item.accounts.select_related('asset').all()
    serializer = PlaidAccountSerializer(accounts, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def sync_balances(request, item_id):
    """Manually sync balances for a Plaid item."""
    try:
        plaid_item = PlaidItem.objects.get(pk=item_id)
    except PlaidItem.DoesNotExist:
        return Response({'error': 'Plaid item not found'}, status=status.HTTP_404_NOT_FOUND)

    if plaid_item.status == 'needs_relink':
        return Response(
            {'error': 'This account needs to be re-linked before syncing.'},
            status=status.HTTP_409_CONFLICT,
        )

    try:
        balances = services.get_balances(plaid_item.access_token)
    except Exception as e:
        logger.error(f"Balance sync failed for item {plaid_item.id}: {e}")
        plaid_item.status = 'error'
        plaid_item.error_message = str(e)
        plaid_item.save()
        return Response(
            {'error': 'Failed to sync with Plaid.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    now = timezone.now()
    today = date.today()
    snapshots_created = 0
    errors = []

    with transaction.atomic():
        for balance_data in balances:
            try:
                account = PlaidAccount.objects.get(
                    plaid_item=plaid_item,
                    account_id=balance_data['account_id'],
                )
            except PlaidAccount.DoesNotExist:
                errors.append(f"Unknown account: {balance_data['account_id']}")
                continue

            current_balance = balance_data.get('current_balance')
            if current_balance is not None:
                account.current_balance = Decimal(str(current_balance))
                account.last_synced = now
                account.save()

                # Create FMV snapshot if account is mapped to an asset
                if account.asset_id:
                    _, created = FMVSnapshot.objects.update_or_create(
                        asset=account.asset,
                        snapshot_date=today,
                        defaults={
                            'value': Decimal(str(current_balance)),
                            'source': 'plaid',
                            'notes': f'Synced from {plaid_item.institution_name} - {account.name}',
                        },
                    )
                    if created:
                        snapshots_created += 1

        plaid_item.last_synced = now
        plaid_item.status = 'active'
        plaid_item.error_message = None
        plaid_item.save()

    return Response({
        'synced_accounts': len(balances),
        'fmv_snapshots_created': snapshots_created,
        'errors': errors,
        'last_synced': now.isoformat(),
    })


@api_view(['PATCH'])
def map_asset(request, account_id):
    """Map a Plaid account to an existing asset."""
    serializer = MapAssetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        account = PlaidAccount.objects.get(pk=account_id)
    except PlaidAccount.DoesNotExist:
        return Response({'error': 'Plaid account not found'}, status=status.HTTP_404_NOT_FOUND)

    asset_id = serializer.validated_data['asset_id']
    try:
        asset = Asset.objects.get(pk=asset_id)
    except Asset.DoesNotExist:
        return Response({'error': 'Asset not found'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if asset is already mapped to another account
    existing = PlaidAccount.objects.filter(asset=asset).exclude(pk=account.pk).first()
    if existing:
        return Response(
            {'error': f'Asset is already mapped to Plaid account "{existing.name}"'},
            status=status.HTTP_409_CONFLICT,
        )

    account.asset = asset
    account.save()

    return Response({
        'id': account.id,
        'account_id': account.account_id,
        'name': account.name,
        'asset': asset.id,
        'asset_name': asset.name,
    })


@api_view(['DELETE'])
def delete_item(request, item_id):
    """Unlink a Plaid institution. FMV snapshots are preserved."""
    try:
        plaid_item = PlaidItem.objects.get(pk=item_id)
    except PlaidItem.DoesNotExist:
        return Response({'error': 'Plaid item not found'}, status=status.HTTP_404_NOT_FOUND)

    plaid_item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
