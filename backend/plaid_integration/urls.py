from django.urls import path
from . import views

urlpatterns = [
    path('create-link-token/', views.create_link_token, name='plaid-create-link-token'),
    path('exchange-token/', views.exchange_token, name='plaid-exchange-token'),
    path('items/', views.list_items, name='plaid-list-items'),
    path('items/<int:item_id>/accounts/', views.list_item_accounts, name='plaid-item-accounts'),
    path('items/<int:item_id>/sync/', views.sync_balances, name='plaid-sync-balances'),
    path('items/<int:item_id>/', views.delete_item, name='plaid-delete-item'),
    path('accounts/<int:account_id>/map-asset/', views.map_asset, name='plaid-map-asset'),
]
