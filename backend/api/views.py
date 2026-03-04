from django.http import HttpResponse
from django.db import transaction
from decimal import Decimal
from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import (
    Entity, Asset, EntityAssetOwnership, Distribution,
    DistributionAllocation, Budget, BudgetLineItem,
    AssetTag, FMVSnapshot, Commitment, CapitalCall,
)
from .serializers import (
    EntitySerializer, AssetSerializer, EntityAssetOwnershipSerializer,
    DistributionSerializer, DistributionWriteSerializer, DistributionAllocationSerializer,
    BudgetSerializer, BudgetWriteSerializer, BudgetLineItemSerializer,
    AssetTagSerializer, FMVSnapshotSerializer,
    CommitmentSerializer, CapitalCallSerializer,
)
from .reports import (
    generate_distribution_report, generate_dashboard_summary,
    generate_portfolio_by_class, generate_net_worth_summary, generate_fmv_report,
    generate_portfolio_summary, generate_asset_class_summary,
    generate_investment_performance,
)
from .excel_export import export_distribution_report
from .performance import get_asset_performance, get_entity_performance, get_performance_summary


class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.prefetch_related('tags', 'fmv_snapshots').all()
    serializer_class = AssetSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filtering by asset_type
        asset_type = self.request.query_params.get('asset_type')
        if asset_type:
            qs = qs.filter(asset_type=asset_type)
        # Filtering by tag slug (multi-value: ?tag=illiquid&tag=domestic)
        tags = self.request.query_params.getlist('tag')
        if tags:
            for tag_slug in tags:
                qs = qs.filter(tags__slug=tag_slug)
        # Filter: has_fmv — assets with at least one FMV snapshot
        has_fmv = self.request.query_params.get('has_fmv')
        if has_fmv is not None:
            if has_fmv.lower() in ('true', '1'):
                qs = qs.filter(fmv_snapshots__isnull=False).distinct()
            elif has_fmv.lower() in ('false', '0'):
                qs = qs.filter(fmv_snapshots__isnull=True)
        # Filter: plaid_linked — assets mapped to a Plaid account
        plaid_linked = self.request.query_params.get('plaid_linked')
        if plaid_linked is not None:
            if plaid_linked.lower() in ('true', '1'):
                qs = qs.filter(plaid_accounts__isnull=False).distinct()
            elif plaid_linked.lower() in ('false', '0'):
                qs = qs.filter(plaid_accounts__isnull=True)
        return qs

    @action(detail=True, methods=['get'], url_path='fmv-history')
    def fmv_history(self, request, pk=None):
        """Return the FMV timeline for a specific asset with change indicators."""
        asset = self.get_object()
        snapshots = asset.fmv_snapshots.order_by('-snapshot_date')

        result = []
        snapshot_list = list(snapshots)
        for i, snap in enumerate(snapshot_list):
            entry = {
                'snapshot_date': snap.snapshot_date,
                'value': str(snap.value),
                'source': snap.source,
                'change_amount': None,
                'change_pct': None,
            }
            # Compare to the next (older) snapshot
            if i < len(snapshot_list) - 1:
                prev = snapshot_list[i + 1]
                change = snap.value - prev.value
                entry['change_amount'] = str(change)
                if prev.value and prev.value != 0:
                    pct = (change / prev.value * 100).quantize(Decimal('0.01'))
                    entry['change_pct'] = str(pct)
            result.append(entry)

        latest = snapshot_list[0] if snapshot_list else None
        return Response({
            'asset_id': asset.id,
            'asset_name': asset.name,
            'current_fmv': str(latest.value) if latest else None,
            'current_fmv_date': str(latest.snapshot_date) if latest else None,
            'snapshots': result,
        })

    @action(detail=True, methods=['post'], url_path='tags')
    def set_tags(self, request, pk=None):
        """Set tags on an asset (replace all existing tags)."""
        asset = self.get_object()
        tag_ids = request.data.get('tag_ids', [])
        tags = list(AssetTag.objects.filter(id__in=tag_ids))
        if len(tags) != len(set(tag_ids)):
            found_ids = {t.id for t in tags}
            missing = [tid for tid in tag_ids if tid not in found_ids]
            return Response(
                {'error': f'Tag IDs not found: {missing}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        asset.tags.set(tags)
        serializer = self.get_serializer(asset)
        return Response(serializer.data)


class FMVSnapshotViewSet(viewsets.ModelViewSet):
    serializer_class = FMVSnapshotSerializer

    def get_queryset(self):
        qs = FMVSnapshot.objects.select_related('asset').all()
        # Filter by asset
        asset_id = self.request.query_params.get('asset')
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        # Filter by source
        source = self.request.query_params.get('source')
        if source:
            qs = qs.filter(source=source)
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(snapshot_date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(snapshot_date__lte=date_to)
        return qs


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


class AssetTagViewSet(viewsets.ModelViewSet):
    serializer_class = AssetTagSerializer

    def get_queryset(self):
        from django.db.models import Count
        return AssetTag.objects.annotate(assets_count=Count('assets')).all()


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


def _parse_fmv_params(data):
    """Parse FMV report request parameters."""
    type_filters = data.get('type_filters')
    if type_filters and isinstance(type_filters, list):
        type_filters = [str(t) for t in type_filters if t]
    elif type_filters and isinstance(type_filters, str):
        type_filters = [t.strip() for t in type_filters.split(',') if t.strip()]
    else:
        type_filters = None

    entity_ids_raw = data.get('entity_ids')
    entity_ids = None
    if entity_ids_raw:
        if isinstance(entity_ids_raw, (list, tuple)):
            entity_ids = [int(v) for v in entity_ids_raw if str(v).strip()]
        else:
            entity_ids = [int(item.strip()) for item in str(entity_ids_raw).split(',') if item.strip()]

    return {
        'type_filters': type_filters if type_filters else None,
        'entity_ids': entity_ids if entity_ids else None,
    }


@api_view(['POST'])
def fmv_report(request):
    """POST /api/reports/fmv/generate/ — Generate FMV report."""
    params = _parse_fmv_params(request.data)
    report = generate_fmv_report(**params)
    return Response(report)


@api_view(['POST'])
def fmv_export(request):
    """POST /api/reports/fmv/export/ — Export FMV report to Excel."""
    from .excel_export import export_fmv_report
    params = _parse_fmv_params(request.data)
    report = generate_fmv_report(**params)
    excel_buf = export_fmv_report(report)
    today = date.today().isoformat()
    filename = f"fmv_report_{today}.xlsx"
    response = HttpResponse(
        excel_buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
def dashboard_summary(request):
    """Quick KPI summary for the dashboard, including net worth."""
    data = generate_dashboard_summary()
    # Add net worth summary
    net_worth = generate_net_worth_summary()
    data['net_worth'] = net_worth
    return Response(data)


@api_view(['GET'])
def portfolio_by_class(request):
    """GET /api/reports/portfolio-by-class/ — portfolio allocation by asset type."""
    entity_ids = request.query_params.getlist('entity_id')
    tag_slugs = request.query_params.getlist('tag')
    entity_ids = [int(eid) for eid in entity_ids if eid] or None
    tag_slugs = tag_slugs or None
    data = generate_portfolio_by_class(entity_ids=entity_ids, tag_slugs=tag_slugs)
    return Response(data)


# ---------------------------------------------------------------------------
# Performance endpoints (T043-T045)
# ---------------------------------------------------------------------------


@api_view(['GET'])
def asset_performance(request, pk):
    """GET /api/assets/{id}/performance/ — performance metrics for a single asset."""
    try:
        Asset.objects.get(pk=pk)
    except Asset.DoesNotExist:
        return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)
    calc_date_str = request.query_params.get('calc_date')
    calc_date = None
    if calc_date_str:
        try:
            calc_date = date.fromisoformat(calc_date_str)
        except ValueError:
            return Response({'error': 'Invalid calc_date format (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
    data = get_asset_performance(pk, calc_date)
    return Response(data)


@api_view(['GET'])
def entity_performance(request, pk):
    """GET /api/entities/{id}/performance/ — ownership-weighted performance for an entity."""
    try:
        Entity.objects.get(pk=pk)
    except Entity.DoesNotExist:
        return Response({'error': 'Entity not found'}, status=status.HTTP_404_NOT_FOUND)
    calc_date_str = request.query_params.get('calc_date')
    calc_date = None
    if calc_date_str:
        try:
            calc_date = date.fromisoformat(calc_date_str)
        except ValueError:
            return Response({'error': 'Invalid calc_date format (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
    data = get_entity_performance(pk, calc_date)
    return Response(data)


@api_view(['GET'])
def performance_summary(request):
    """GET /api/performance/summary/ — portfolio-wide performance summary."""
    calc_date_str = request.query_params.get('calc_date')
    calc_date = None
    if calc_date_str:
        try:
            calc_date = date.fromisoformat(calc_date_str)
        except ValueError:
            return Response({'error': 'Invalid calc_date format (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
    data = get_performance_summary(calc_date)
    return Response(data)


# ---------------------------------------------------------------------------
# Commitment / Capital-Call CRUD ViewSets
# ---------------------------------------------------------------------------

class CommitmentViewSet(viewsets.ModelViewSet):
    """CRUD for Commitment records.

    Supports query-string filters:
        ?entity=<id>   — filter by entity
        ?asset=<id>    — filter by asset
    """
    serializer_class = CommitmentSerializer

    def get_queryset(self):
        qs = Commitment.objects.select_related('entity', 'asset').all()
        entity_id = self.request.query_params.get('entity')
        asset_id = self.request.query_params.get('asset')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        return qs

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as exc:
            if 'unique' in str(exc).lower():
                return Response(
                    {'error': 'A commitment already exists for this entity/asset pair.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise


class CapitalCallViewSet(viewsets.ModelViewSet):
    """CRUD for CapitalCall records.

    Supports query-string filters:
        ?commitment=<id> — filter by commitment
    """
    serializer_class = CapitalCallSerializer

    def get_queryset(self):
        qs = CapitalCall.objects.select_related('commitment', 'commitment__entity', 'commitment__asset').all()
        commitment_id = self.request.query_params.get('commitment')
        if commitment_id:
            qs = qs.filter(commitment_id=commitment_id)
        return qs


# ---------------------------------------------------------------------------
# Portfolio Tracker API Views
# ---------------------------------------------------------------------------

def _parse_portfolio_params(data):
    """Parse common portfolio request parameters (entity_ids, as_of_date, type_filters)."""
    entity_ids_raw = data.get('entity_ids')
    entity_ids = None
    if entity_ids_raw:
        if isinstance(entity_ids_raw, (list, tuple)):
            entity_ids = [int(v) for v in entity_ids_raw if str(v).strip()]
        else:
            entity_ids = [int(item.strip()) for item in str(entity_ids_raw).split(',') if item.strip()]

    as_of_date = None
    as_of_raw = data.get('as_of_date')
    if as_of_raw:
        try:
            as_of_date = date.fromisoformat(str(as_of_raw))
        except ValueError:
            pass  # fall back to None → reports default to today

    type_filters = data.get('type_filters')
    if type_filters and isinstance(type_filters, list):
        type_filters = [str(t) for t in type_filters if t]
    elif type_filters and isinstance(type_filters, str):
        type_filters = [t.strip() for t in type_filters.split(',') if t.strip()]
    else:
        type_filters = None

    return {
        'entity_ids': entity_ids if entity_ids else None,
        'as_of_date': as_of_date,
        'type_filters': type_filters if type_filters else None,
    }


@api_view(['POST'])
def portfolio_summary(request):
    """POST /api/portfolio/summary/ — Entity-level portfolio rollup."""
    params = _parse_portfolio_params(request.data)
    report = generate_portfolio_summary(
        entity_ids=params['entity_ids'],
        as_of_date=params['as_of_date'],
    )
    return Response(report)


@api_view(['POST'])
def asset_class_summary(request):
    """POST /api/portfolio/asset-class-summary/ — Asset-class breakdown."""
    params = _parse_portfolio_params(request.data)
    report = generate_asset_class_summary(
        entity_ids=params['entity_ids'],
        type_filters=params['type_filters'],
    )
    return Response(report)


@api_view(['POST'])
def investment_performance(request):
    """POST /api/portfolio/performance/ — Per-investment performance."""
    params = _parse_portfolio_params(request.data)
    report = generate_investment_performance(
        entity_ids=params['entity_ids'],
        as_of_date=params['as_of_date'],
    )
    return Response(report)


# ---------------------------------------------------------------------------
# Portfolio Excel Export Views
# ---------------------------------------------------------------------------

@api_view(['POST'])
def portfolio_summary_export(request):
    """POST /api/portfolio/summary/export/ — Export portfolio summary to Excel."""
    from .excel_export import export_portfolio_summary as _export
    params = _parse_portfolio_params(request.data)
    report = generate_portfolio_summary(
        entity_ids=params['entity_ids'],
        as_of_date=params['as_of_date'],
    )
    excel_buf = _export(report)
    today = date.today().isoformat()
    filename = f"portfolio_summary_{today}.xlsx"
    response = HttpResponse(
        excel_buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['POST'])
def asset_class_summary_export(request):
    """POST /api/portfolio/asset-class-summary/export/ — Export asset-class summary to Excel."""
    from .excel_export import export_asset_class_summary as _export
    params = _parse_portfolio_params(request.data)
    report = generate_asset_class_summary(
        entity_ids=params['entity_ids'],
        type_filters=params['type_filters'],
    )
    excel_buf = _export(report)
    today = date.today().isoformat()
    filename = f"asset_class_summary_{today}.xlsx"
    response = HttpResponse(
        excel_buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['POST'])
def investment_performance_export(request):
    """POST /api/portfolio/performance/export/ — Export investment performance to Excel."""
    from .excel_export import export_investment_performance as _export
    params = _parse_portfolio_params(request.data)
    report = generate_investment_performance(
        entity_ids=params['entity_ids'],
        as_of_date=params['as_of_date'],
    )
    excel_buf = _export(report)
    today = date.today().isoformat()
    filename = f"investment_performance_{today}.xlsx"
    response = HttpResponse(
        excel_buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
