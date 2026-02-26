from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'entities', views.EntityViewSet)
router.register(r'assets', views.AssetViewSet)
router.register(r'ownerships', views.EntityAssetOwnershipViewSet)
router.register(r'distributions', views.DistributionViewSet)
router.register(r'distribution-allocations', views.DistributionAllocationViewSet)
router.register(r'budgets', views.BudgetViewSet)
router.register(r'budget-line-items', views.BudgetLineItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('reports/generate/', views.generate_report, name='report-generate'),
    path('reports/export/', views.export_report, name='report-export'),
]
