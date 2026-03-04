from django.contrib import admin
from .models import (
    Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation,
    Commitment, CapitalCall,
)

admin.site.register(Entity)
admin.site.register(Asset)
admin.site.register(EntityAssetOwnership)
admin.site.register(Distribution)
admin.site.register(DistributionAllocation)


@admin.register(Commitment)
class CommitmentAdmin(admin.ModelAdmin):
    list_display = ['entity', 'asset', 'commitment_date', 'original_amount']
    list_filter = ['entity', 'asset']
    search_fields = ['entity__name', 'asset__name']


@admin.register(CapitalCall)
class CapitalCallAdmin(admin.ModelAdmin):
    list_display = ['commitment', 'call_date', 'amount']
    list_filter = ['commitment__entity', 'commitment__asset']
    search_fields = ['commitment__entity__name', 'commitment__asset__name']
