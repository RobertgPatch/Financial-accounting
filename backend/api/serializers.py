from rest_framework import serializers
from .models import Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = '__all__'


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'


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


class DistributionSerializer(serializers.ModelSerializer):
    allocations = DistributionAllocationSerializer(many=True, read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)

    class Meta:
        model = Distribution
        fields = '__all__'


class DistributionWriteSerializer(serializers.ModelSerializer):
    allocations = DistributionAllocationSerializer(many=True, required=False)

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
