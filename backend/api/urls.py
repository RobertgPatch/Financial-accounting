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
router.register(r'fmv-snapshots', views.FMVSnapshotViewSet, basename='fmvsnapshot')
router.register(r'tags', views.AssetTagViewSet, basename='assettag')
router.register(r'commitments', views.CommitmentViewSet, basename='commitment')
router.register(r'capital-calls', views.CapitalCallViewSet, basename='capitalcall')

urlpatterns = [
    path('', include(router.urls)),
    path('reports/generate/', views.generate_report, name='report-generate'),
    path('reports/export/', views.export_report, name='report-export'),
    path('reports/fmv/generate/', views.fmv_report, name='fmv-report-generate'),
    path('reports/fmv/export/', views.fmv_export, name='fmv-report-export'),
    path('reports/dashboard-summary/', views.dashboard_summary, name='dashboard-summary'),
    path('reports/portfolio-by-class/', views.portfolio_by_class, name='portfolio-by-class'),
    # Portfolio tracker endpoints
    path('portfolio/summary/', views.portfolio_summary, name='portfolio-summary'),
    path('portfolio/asset-class-summary/', views.asset_class_summary, name='asset-class-summary'),
    path('portfolio/performance/', views.investment_performance, name='investment-performance'),
    path('portfolio/summary/export/', views.portfolio_summary_export, name='portfolio-summary-export'),
    path('portfolio/asset-class-summary/export/', views.asset_class_summary_export, name='asset-class-summary-export'),
    path('portfolio/performance/export/', views.investment_performance_export, name='investment-performance-export'),
    # Performance endpoints
    path('assets/<int:pk>/performance/', views.asset_performance, name='asset-performance'),
    path('entities/<int:pk>/performance/', views.entity_performance, name='entity-performance'),
    path('performance/summary/', views.performance_summary, name='performance-summary'),
]
