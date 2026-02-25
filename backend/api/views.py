from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation
from .serializers import (
    EntitySerializer, AssetSerializer, EntityAssetOwnershipSerializer,
    DistributionSerializer, DistributionWriteSerializer, DistributionAllocationSerializer,
)
from .reports import generate_distribution_report
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


class DistributionAllocationViewSet(viewsets.ModelViewSet):
    queryset = DistributionAllocation.objects.select_related('entity', 'distribution').all()
    serializer_class = DistributionAllocationSerializer


def _parse_report_params(data):
    return {
        'period_type': data.get('period_type', 'yearly'),
        'year': int(data.get('year', 2024)),
        'quarter': int(data['quarter']) if data.get('quarter') else None,
        'month': int(data['month']) if data.get('month') else None,
        'entity_ids': data.get('entity_ids') or None,
        'asset_ids': data.get('asset_ids') or None,
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
