from django.http import HttpResponse
from django.db import transaction
from decimal import Decimal
from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation, Budget, BudgetLineItem
from .serializers import (
    EntitySerializer, AssetSerializer, EntityAssetOwnershipSerializer,
    DistributionSerializer, DistributionWriteSerializer, DistributionAllocationSerializer,
    BudgetSerializer, BudgetWriteSerializer, BudgetLineItemSerializer,
)
from .reports import generate_distribution_report, generate_dashboard_summary
from .excel_export import export_distribution_report


class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer


class EntityAssetOwnershipViewSet(viewsets.ModelViewSet):
    queryset = EntityAssetOwnership.objects.select_related('entity', 'asset').all()
    serializer_class = EntityAssetOwnershipSerializer


class DistributionViewSet(viewsets.ModelViewSet):
    queryset = Distribution.objects.select_related('asset').prefetch_related('allocations__entity').all()

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return DistributionWriteSerializer
        return DistributionSerializer

    @action(detail=True, methods=['post'], url_path='auto-allocate')
    def auto_allocate(self, request, pk=None):
        """
        Auto-allocate a distribution based on current ownership percentages.
        Deletes existing allocations and creates new ones from EntityAssetOwnership.
        """
        distribution = self.get_object()
        ownerships = EntityAssetOwnership.objects.filter(
            asset=distribution.asset
        ).select_related('entity').order_by('entity__name')

        if not ownerships.exists():
            return Response(
                {'error': 'No ownership records found for this asset. Add ownerships first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_pct = sum(o.percentage for o in ownerships)
        if total_pct <= 0:
            return Response(
                {'error': 'Total ownership percentage is zero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete existing allocations and create fresh ones within a single atomic operation
        with transaction.atomic():
            distribution.allocations.all().delete()
            allocations = []
            remaining = distribution.total_amount
            ownership_list = list(ownerships)

            for i, ownership in enumerate(ownership_list):
                pct = ownership.percentage
                if i == len(ownership_list) - 1:
                    # Last allocation gets the remainder to avoid rounding issues
                    amount = remaining
                else:
                    amount = (pct / total_pct * distribution.total_amount).quantize(Decimal('0.01'))
                    remaining -= amount

                alloc = DistributionAllocation.objects.create(
                    distribution=distribution,
                    entity=ownership.entity,
                    amount=amount,
                    percentage=pct,
                )
                allocations.append(alloc)

        # Reload to avoid returning a stale prefetch cache after delete/create
        distribution = Distribution.objects.select_related('asset').prefetch_related('allocations__entity').get(pk=distribution.pk)
        serializer = DistributionSerializer(distribution)
        return Response(serializer.data)


class DistributionAllocationViewSet(viewsets.ModelViewSet):
    queryset = DistributionAllocation.objects.select_related('entity', 'distribution').all()
    serializer_class = DistributionAllocationSerializer


class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.prefetch_related('line_items__asset', 'line_items__entity').all()

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return BudgetWriteSerializer
        return BudgetSerializer


class BudgetLineItemViewSet(viewsets.ModelViewSet):
    queryset = BudgetLineItem.objects.select_related('budget', 'asset', 'entity').all()
    serializer_class = BudgetLineItemSerializer


def _parse_report_params(data):
    def _normalize_ids(value):
        if not value:
            return None
        if isinstance(value, (list, tuple)):
            return [int(v) for v in value if str(v).strip()]
        return [int(item.strip()) for item in str(value).split(',') if item.strip()]

    return {
        'period_type': data.get('period_type', 'yearly'),
        'year': int(data.get('year', date.today().year)),
        'quarter': int(data['quarter']) if data.get('quarter') else None,
        'month': int(data['month']) if data.get('month') else None,
        'entity_ids': _normalize_ids(data.get('entity_ids')),
        'asset_ids': _normalize_ids(data.get('asset_ids')),
    }


@api_view(['POST'])
def generate_report(request):
    params = _parse_report_params(request.data)
    report = generate_distribution_report(**params)
    return Response(report)


@api_view(['POST'])
def export_report(request):
    params = _parse_report_params(request.data)
    report = generate_distribution_report(**params)
    excel_buf = export_distribution_report(report)
    period = report['period']
    filename = f"distribution_report_{period['year']}"
    if period['quarter']:
        filename += f"_Q{period['quarter']}"
    if period['month']:
        filename += f"_M{period['month']:02d}"
    filename += '.xlsx'
    response = HttpResponse(
        excel_buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
def dashboard_summary(request):
    """Quick KPI summary for the dashboard."""
    data = generate_dashboard_summary()
    return Response(data)
