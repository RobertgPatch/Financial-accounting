from rest_framework import serializers
from .models import PlaidItem, PlaidAccount


class PlaidAccountSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True, default=None)

    class Meta:
        model = PlaidAccount
        fields = [
            'id', 'account_id', 'name', 'mask', 'type', 'subtype',
            'asset', 'asset_name', 'current_balance', 'last_synced', 'created_at',
        ]
        read_only_fields = ['id', 'account_id', 'name', 'mask', 'type', 'subtype', 'created_at']


class PlaidItemSerializer(serializers.ModelSerializer):
    accounts_count = serializers.IntegerField(source='accounts.count', read_only=True)

    class Meta:
        model = PlaidItem
        fields = [
            'id', 'institution_name', 'status', 'last_synced',
            'accounts_count', 'created_at',
        ]
        read_only_fields = fields


class ExchangeTokenSerializer(serializers.Serializer):
    public_token = serializers.CharField(required=True)
    institution = serializers.DictField(required=False, default=dict)
    accounts = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class MapAssetSerializer(serializers.Serializer):
    asset_id = serializers.IntegerField(required=True)
