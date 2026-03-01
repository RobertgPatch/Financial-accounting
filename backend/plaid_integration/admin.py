from django.contrib import admin
from .models import PlaidItem, PlaidAccount


@admin.register(PlaidItem)
class PlaidItemAdmin(admin.ModelAdmin):
    list_display = ('institution_name', 'status', 'last_synced', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('item_id', 'access_token', 'created_at', 'updated_at')


@admin.register(PlaidAccount)
class PlaidAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'mask', 'type', 'subtype', 'asset', 'current_balance')
    list_filter = ('type',)
    raw_id_fields = ('plaid_item', 'asset')
