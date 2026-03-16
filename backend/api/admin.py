from django.contrib import admin
from .models import (
    Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation,
    Commitment, CapitalCall,
    K1Document, K1PartnershipInfo, K1PartnerInfo, K1IncomeItem, K1CapitalAccount,
    Activity,
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


class K1PartnershipInfoInline(admin.StackedInline):
    model = K1PartnershipInfo
    extra = 0


class K1PartnerInfoInline(admin.StackedInline):
    model = K1PartnerInfo
    extra = 0


class K1IncomeItemInline(admin.TabularInline):
    model = K1IncomeItem
    extra = 0


class K1CapitalAccountInline(admin.StackedInline):
    model = K1CapitalAccount
    extra = 0


@admin.register(K1Document)
class K1DocumentAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'tax_year', 'status', 'entity', 'asset', 'uploaded_at']
    list_filter = ['status', 'tax_year', 'extraction_method']
    search_fields = ['original_filename', 'partnership_info__name', 'partner_info__name']
    inlines = [K1PartnershipInfoInline, K1PartnerInfoInline, K1IncomeItemInline, K1CapitalAccountInline]


admin.site.register(K1PartnershipInfo)
admin.site.register(K1PartnerInfo)
admin.site.register(K1IncomeItem)
admin.site.register(K1CapitalAccount)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['year', 'entity', 'asset', 'contributions', 'total_income',
                    'distributions', 'ending_tax_basis', 'negative_basis']
    list_filter = ['year', 'entity', 'asset', 'negative_basis']
    search_fields = ['entity__name', 'asset__name', 'notes']
