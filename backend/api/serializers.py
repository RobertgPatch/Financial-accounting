from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum
from .models import (
    Entity, Asset, EntityAssetOwnership, Distribution,
    DistributionAllocation, Budget, BudgetLineItem,
    AssetTag, FMVSnapshot, Commitment, CapitalCall,
)


class AssetTagSerializer(serializers.ModelSerializer):
    assets_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = AssetTag
        fields = ['id', 'name', 'slug', 'color', 'assets_count', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class FMVSnapshotSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)

    class Meta:
        model = FMVSnapshot
        fields = [
            'id', 'asset', 'asset_name', 'snapshot_date', 'value',
            'source', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_value(self, value):
        if value < 0:
            raise serializers.ValidationError('FMV value must be >= 0.')
        return value

    def validate_snapshot_date(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError('Snapshot date cannot be in the future.')
        return value

    def validate(self, data):
        asset = data.get('asset') or (self.instance.asset if self.instance else None)
        snap_date = data.get('snapshot_date') or (self.instance.snapshot_date if self.instance else None)
        if asset and snap_date:
            qs = FMVSnapshot.objects.filter(asset=asset, snapshot_date=snap_date)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    'An FMV snapshot already exists for this asset on this date.'
                )
        return data


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = '__all__'


class AssetSerializer(serializers.ModelSerializer):
    tags = AssetTagSerializer(many=True, read_only=True)
    asset_type_display = serializers.CharField(source='get_asset_type_display', read_only=True)
    latest_fmv = serializers.SerializerMethodField()
    latest_fmv_date = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = '__all__'

    def get_latest_fmv(self, obj):
        snapshot = obj.fmv_snapshots.order_by('-snapshot_date').first()
        return str(snapshot.value) if snapshot else None

    def get_latest_fmv_date(self, obj):
        snapshot = obj.fmv_snapshots.order_by('-snapshot_date').first()
        return str(snapshot.snapshot_date) if snapshot else None


class EntityAssetOwnershipSerializer(serializers.ModelSerializer):
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)

    class Meta:
        model = EntityAssetOwnership
        fields = '__all__'


class DistributionAllocationSerializer(serializers.ModelSerializer):
    entity_name = serializers.CharField(source='entity.name', read_only=True)

    class Meta:
        model = DistributionAllocation
        fields = '__all__'


class NestedAllocationSerializer(serializers.ModelSerializer):
    """Used for nested writes inside DistributionWriteSerializer."""
    class Meta:
        model = DistributionAllocation
        exclude = ['distribution']


class DistributionSerializer(serializers.ModelSerializer):
    allocations = DistributionAllocationSerializer(many=True, read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)

    class Meta:
        model = Distribution
        fields = '__all__'


class DistributionWriteSerializer(serializers.ModelSerializer):
    allocations = NestedAllocationSerializer(many=True, required=False)

    class Meta:
        model = Distribution
        fields = '__all__'

    def create(self, validated_data):
        allocations_data = validated_data.pop('allocations', [])
        distribution = Distribution.objects.create(**validated_data)
        for alloc_data in allocations_data:
            DistributionAllocation.objects.create(distribution=distribution, **alloc_data)
        return distribution

    def update(self, instance, validated_data):
        allocations_data = validated_data.pop('allocations', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if allocations_data is not None:
            instance.allocations.all().delete()
            for alloc_data in allocations_data:
                DistributionAllocation.objects.create(distribution=instance, **alloc_data)
        return instance


class BudgetLineItemSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    entity_name = serializers.CharField(source='entity.name', read_only=True, default=None)

    class Meta:
        model = BudgetLineItem
        fields = '__all__'


class NestedBudgetLineItemSerializer(serializers.ModelSerializer):
    """Used for nested writes inside BudgetWriteSerializer."""
    class Meta:
        model = BudgetLineItem
        exclude = ['budget']


class BudgetSerializer(serializers.ModelSerializer):
    line_items = BudgetLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Budget
        fields = '__all__'


class BudgetWriteSerializer(serializers.ModelSerializer):
    line_items = NestedBudgetLineItemSerializer(many=True, required=False)

    class Meta:
        model = Budget
        fields = '__all__'

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items', [])
        budget = Budget.objects.create(**validated_data)
        for item_data in line_items_data:
            BudgetLineItem.objects.create(budget=budget, **item_data)
        return budget

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if line_items_data is not None:
            instance.line_items.all().delete()
            for item_data in line_items_data:
                BudgetLineItem.objects.create(budget=instance, **item_data)
        return instance


class CommitmentSerializer(serializers.ModelSerializer):
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    paid_in = serializers.SerializerMethodField()
    pct_called = serializers.SerializerMethodField()
    unfunded = serializers.SerializerMethodField()
    call_count = serializers.SerializerMethodField()

    class Meta:
        model = Commitment
        fields = [
            'id', 'entity', 'entity_name', 'asset', 'asset_name',
            'commitment_date', 'original_amount', 'notes',
            'paid_in', 'pct_called', 'unfunded', 'call_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _get_paid_in(self, obj):
        total = obj.capital_calls.aggregate(total=Sum('amount'))['total']
        return total or Decimal('0.00')

    def get_paid_in(self, obj):
        return str(self._get_paid_in(obj))

    def get_pct_called(self, obj):
        if obj.original_amount == 0:
            return None
        paid = self._get_paid_in(obj)
        pct = (paid / obj.original_amount * 100).quantize(Decimal('0.01'))
        return str(pct)

    def get_unfunded(self, obj):
        paid = self._get_paid_in(obj)
        return str(obj.original_amount - paid)

    def get_call_count(self, obj):
        return obj.capital_calls.count()


class CapitalCallSerializer(serializers.ModelSerializer):
    commitment_display = serializers.SerializerMethodField()

    class Meta:
        model = CapitalCall
        fields = [
            'id', 'commitment', 'commitment_display',
            'call_date', 'amount', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_commitment_display(self, obj):
        return f"{obj.commitment.entity.name} → {obj.commitment.asset.name}"
