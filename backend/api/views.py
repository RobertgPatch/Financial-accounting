import logging

from django.http import HttpResponse, FileResponse
from django.db import transaction
from decimal import Decimal
from datetime import date
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from .models import (
    Entity, Asset, EntityAssetOwnership, Distribution,
    DistributionAllocation, Budget, BudgetLineItem,
    AssetTag, FMVSnapshot, Commitment, CapitalCall,
    K1Document, K1PartnershipInfo, K1PartnerInfo, K1IncomeItem, K1CapitalAccount,
    Activity,
)
from .serializers import (
    EntitySerializer, AssetSerializer, EntityAssetOwnershipSerializer,
    DistributionSerializer, DistributionWriteSerializer, DistributionAllocationSerializer,
    BudgetSerializer, BudgetWriteSerializer, BudgetLineItemSerializer,
    AssetTagSerializer, FMVSnapshotSerializer,
    CommitmentSerializer, CapitalCallSerializer,
    K1DocumentSerializer, K1DocumentDetailSerializer,
    K1PartnershipInfoSerializer, K1PartnerInfoSerializer,
    K1IncomeItemSerializer, K1CapitalAccountSerializer,
    ActivitySerializer,
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
# Activity Ledger CRUD ViewSet
# ---------------------------------------------------------------------------

class ActivityViewSet(viewsets.ModelViewSet):
    """CRUD for Activity (tax-basis ledger) records.

    Supports query-string filters:
        ?entity=<id>   — filter by entity
        ?asset=<id>    — filter by asset (partnership)
        ?year=<int>    — filter by year

    When a specific year is requested the view auto-scaffolds Activity rows
    for every EntityAssetOwnership pair that does not yet have one for that
    year.  Beginning Basis, Ending Tax Basis, Δ vs prior year and other
    derived fields are auto-computed by Activity.save().
    """
    serializer_class = ActivitySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Activity.objects.select_related('entity', 'asset', 'source_k1_document').all()
        entity_id = self.request.query_params.get('entity')
        asset_id = self.request.query_params.get('asset')
        year = self.request.query_params.get('year')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if year:
            qs = qs.filter(year=int(year))
        return qs

    # ------------------------------------------------------------------
    # Auto-scaffold
    # ------------------------------------------------------------------

    def list(self, request, *args, **kwargs):
        year = request.query_params.get('year')
        if year:
            self._scaffold(int(year))
        return super().list(request, *args, **kwargs)

    @staticmethod
    def _scaffold(year):
        """Create Activity rows for every EntityAssetOwnership pair missing for *year*.

        Activity.save() auto-populates beginning_basis from the prior year's
        ending_tax_basis and computes all derived fields.
        """
        pairs = set(
            EntityAssetOwnership.objects.values_list('entity_id', 'asset_id').distinct()
        )
        existing = set(
            Activity.objects.filter(year=year).values_list('entity_id', 'asset_id')
        )
        for entity_id, asset_id in pairs - existing:
            Activity.objects.create(year=year, entity_id=entity_id, asset_id=asset_id)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as exc:
            if 'unique' in str(exc).lower():
                return Response(
                    {'error': 'An activity record already exists for this entity/asset/year combination.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise


# ---------------------------------------------------------------------------
# Portfolio Tracker API Views
# ---------------------------------------------------------------------------

def _parse_portfolio_params(data):
    """Parse common portfolio request parameters (entity_ids, as_of_date, start_date, end_date, type_filters)."""
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

    # Date range filtering
    start_date = None
    start_raw = data.get('start_date')
    if start_raw:
        try:
            start_date = date.fromisoformat(str(start_raw))
        except ValueError:
            pass

    end_date = None
    end_raw = data.get('end_date')
    if end_raw:
        try:
            end_date = date.fromisoformat(str(end_raw))
        except ValueError:
            pass

    # If end_date provided but no as_of_date, use end_date as as_of_date
    if end_date and not as_of_date:
        as_of_date = end_date

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
        'start_date': start_date,
        'end_date': end_date,
        'type_filters': type_filters if type_filters else None,
    }


@api_view(['POST'])
def portfolio_summary(request):
    """POST /api/portfolio/summary/ — Entity-level portfolio rollup."""
    params = _parse_portfolio_params(request.data)
    report = generate_portfolio_summary(
        entity_ids=params['entity_ids'],
        as_of_date=params['as_of_date'],
        start_date=params['start_date'],
        end_date=params['end_date'],
    )
    return Response(report)


@api_view(['POST'])
def asset_class_summary(request):
    """POST /api/portfolio/asset-class-summary/ — Asset-class breakdown."""
    params = _parse_portfolio_params(request.data)
    report = generate_asset_class_summary(
        entity_ids=params['entity_ids'],
        type_filters=params['type_filters'],
        as_of_date=params['as_of_date'],
        start_date=params['start_date'],
        end_date=params['end_date'],
    )
    return Response(report)


@api_view(['POST'])
def investment_performance(request):
    """POST /api/portfolio/performance/ — Per-investment performance."""
    params = _parse_portfolio_params(request.data)
    report = generate_investment_performance(
        entity_ids=params['entity_ids'],
        as_of_date=params['as_of_date'],
        start_date=params['start_date'],
        end_date=params['end_date'],
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
        start_date=params['start_date'],
        end_date=params['end_date'],
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
        as_of_date=params['as_of_date'],
        start_date=params['start_date'],
        end_date=params['end_date'],
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
        start_date=params['start_date'],
        end_date=params['end_date'],
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


@api_view(['POST'])
def activity_export(request):
    """POST /api/activity/export/ — Export activity ledger to Excel."""
    from .excel_export import export_activity_report
    entity_id = request.data.get('entity')
    asset_id = request.data.get('asset')
    year = request.data.get('year')

    qs = Activity.objects.select_related('entity', 'asset').order_by('entity__name', 'asset__name', 'year')
    if entity_id:
        qs = qs.filter(entity_id=entity_id)
    if asset_id:
        qs = qs.filter(asset_id=asset_id)
    if year:
        qs = qs.filter(year=int(year))

    excel_buf = export_activity_report(list(qs))
    today = date.today().isoformat()
    filename = f"activity_report_{today}.xlsx"
    response = HttpResponse(
        excel_buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# K-1 Document ViewSet
# ---------------------------------------------------------------------------

class K1DocumentViewSet(viewsets.ModelViewSet):
    """CRUD + custom actions for K-1 PDF documents.

    Endpoints:
        POST   /api/k1-documents/upload/     — Upload & extract
        GET    /api/k1-documents/            — List (filterable)
        GET    /api/k1-documents/{id}/       — Detail
        PUT    /api/k1-documents/{id}/       — Update extracted fields
        DELETE /api/k1-documents/{id}/       — Delete (draft only)
        POST   /api/k1-documents/{id}/confirm/  — Confirm & lock
        GET    /api/k1-documents/{id}/download/  — Download original PDF
        POST   /api/k1-documents/{id}/populate/  — Auto-populate portfolio
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return K1DocumentSerializer
        return K1DocumentDetailSerializer

    def get_queryset(self):
        qs = K1Document.objects.select_related(
            'entity', 'asset', 'partnership_info', 'partner_info', 'capital_account',
        ).prefetch_related('income_items').all()

        # Filters
        tax_year = self.request.query_params.get('tax_year')
        if tax_year:
            qs = qs.filter(tax_year=tax_year)
        doc_status = self.request.query_params.get('status')
        if doc_status:
            qs = qs.filter(status=doc_status)
        entity_id = self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        asset_type = self.request.query_params.get('asset_type')
        if asset_type:
            qs = qs.filter(asset_type_classification=asset_type)
        return qs

    # ---- Upload & Extract (T028-T029) ----

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """Upload a K-1 PDF, extract data, and create child records atomically."""
        from .k1_parser import parse_k1_document

        pdf_file = request.FILES.get('document')
        if not pdf_file:
            return Response(
                {'error': 'No PDF file provided. Include a "document" field.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tax_year = request.data.get('tax_year')
        if not tax_year:
            return Response(
                {'error': 'tax_year is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tax_year = int(tax_year)
        except (ValueError, TypeError):
            return Response(
                {'error': 'tax_year must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # 1) Create the K1Document record
                k1_doc = K1Document(
                    tax_year=tax_year,
                    document=pdf_file,
                    original_filename=pdf_file.name,
                    entity_id=request.data.get('entity') or None,
                    asset_id=request.data.get('asset') or None,
                    notes=request.data.get('notes', ''),
                )
                k1_doc.save()

                # 2) Run the parser on the saved file
                try:
                    parsed = parse_k1_document(k1_doc.document.path)
                except ValueError as parse_err:
                    # Parser couldn't recognise the document
                    k1_doc.notes = f"Parse warning: {parse_err}"
                    k1_doc.save(update_fields=['notes'])
                    # Still return the document — user can manually enter data
                    serializer = K1DocumentDetailSerializer(k1_doc)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)

                # 3) Update document-level fields from header
                k1_doc.extraction_method = parsed.get('extraction_method', 'text')
                if parsed.get('tax_year'):
                    k1_doc.tax_year = parsed['tax_year']
                k1_doc.is_final = parsed.get('is_final', False)
                k1_doc.is_amended = parsed.get('is_amended', False)
                if parsed.get('warnings'):
                    k1_doc.notes = '\n'.join(parsed['warnings'])
                k1_doc.save()

                # 4) Create child records
                p_info = parsed.get('partnership_info', {})
                if p_info:
                    K1PartnershipInfo.objects.create(document=k1_doc, **p_info)

                pt_info = parsed.get('partner_info', {})
                if pt_info:
                    K1PartnerInfo.objects.create(document=k1_doc, **pt_info)

                for item_data in parsed.get('income_items', []):
                    is_supp = item_data.pop('is_supplemental', False)
                    K1IncomeItem.objects.create(
                        document=k1_doc,
                        is_supplemental=is_supp,
                        **item_data,
                    )

                cap = parsed.get('capital_account', {})
                if cap:
                    K1CapitalAccount.objects.create(document=k1_doc, **cap)

            # Re-fetch with relations for response
            k1_doc.refresh_from_db()
            serializer = K1DocumentDetailSerializer(k1_doc)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception('K-1 upload failed')
            return Response(
                {'error': f'Upload failed: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ---- Update extracted fields (T034) ----

    def update(self, request, *args, **kwargs):
        """Update extracted fields for a draft K-1 document.

        Accepts nested partnership_info, partner_info, income_items[],
        capital_account as flat JSON. Only allowed while status is draft.
        """
        k1_doc = self.get_object()
        if k1_doc.status == 'confirmed':
            return Response(
                {'error': 'Cannot edit a confirmed document.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Update document-level fields
            for field in ('tax_year', 'asset_type_classification', 'is_final',
                          'is_amended', 'notes'):
                if field in request.data:
                    setattr(k1_doc, field, request.data[field])
            # FK fields need special handling for null
            for fk_field in ('entity', 'asset'):
                if fk_field in request.data:
                    val = request.data[fk_field]
                    setattr(k1_doc, f'{fk_field}_id', val if val else None)
            k1_doc.save()

            # Update partnership_info
            pi_data = request.data.get('partnership_info')
            if pi_data and isinstance(pi_data, dict):
                K1PartnershipInfo.objects.update_or_create(
                    document=k1_doc,
                    defaults=pi_data,
                )

            # Update partner_info
            pt_data = request.data.get('partner_info')
            if pt_data and isinstance(pt_data, dict):
                # Clean empty strings for decimal fields
                decimal_fields = {
                    'profit_beginning_pct', 'profit_ending_pct',
                    'loss_beginning_pct', 'loss_ending_pct',
                    'capital_beginning_pct', 'capital_ending_pct',
                    'nonrecourse_beginning', 'nonrecourse_ending',
                    'qualified_nonrecourse_beginning', 'qualified_nonrecourse_ending',
                    'recourse_beginning', 'recourse_ending',
                    'section_704c_beginning', 'section_704c_ending',
                }
                cleaned_pt = {}
                for k, v in pt_data.items():
                    if k in decimal_fields and v in ('', None):
                        cleaned_pt[k] = None
                    else:
                        cleaned_pt[k] = v
                K1PartnerInfo.objects.update_or_create(
                    document=k1_doc,
                    defaults=cleaned_pt,
                )

            # Update income_items (replace-all strategy)
            items_data = request.data.get('income_items')
            if items_data is not None and isinstance(items_data, list):
                k1_doc.income_items.all().delete()
                for item in items_data:
                    # Clean up empty strings for nullable numeric fields
                    cleaned = {}
                    for k, v in item.items():
                        if k == 'amount' and v in ('', None):
                            cleaned[k] = None
                        else:
                            cleaned[k] = v
                    K1IncomeItem.objects.create(document=k1_doc, **cleaned)

            # Update capital_account
            cap_data = request.data.get('capital_account')
            if cap_data and isinstance(cap_data, dict):
                # Clean empty strings for decimal fields
                cleaned_cap = {}
                for k, v in cap_data.items():
                    if v == '' and k != 'tax_basis_method':
                        cleaned_cap[k] = None
                    else:
                        cleaned_cap[k] = v
                K1CapitalAccount.objects.update_or_create(
                    document=k1_doc,
                    defaults=cleaned_cap,
                )

        k1_doc.refresh_from_db()
        serializer = K1DocumentDetailSerializer(k1_doc)
        return Response(serializer.data)

    # ---- Confirm (T035) ----

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """Transition a draft document to confirmed status."""
        k1_doc = self.get_object()
        if k1_doc.status == 'confirmed':
            return Response(
                {'error': 'Document is already confirmed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        k1_doc.status = 'confirmed'
        k1_doc.confirmed_at = timezone.now()
        k1_doc.save(update_fields=['status', 'confirmed_at'])

        k1_doc.refresh_from_db()
        serializer = K1DocumentDetailSerializer(k1_doc)
        return Response(serializer.data)

    # ---- Delete with file cleanup (T044) ----

    def destroy(self, request, *args, **kwargs):
        """Delete a K-1 document and its associated PDF file."""
        k1_doc = self.get_object()
        # Clean up the PDF file from disk
        if k1_doc.document:
            try:
                k1_doc.document.delete(save=False)
            except Exception:
                pass
        return super().destroy(request, *args, **kwargs)

    # ---- Download original PDF (T045) ----

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """Return the original PDF file for download."""
        k1_doc = self.get_object()
        if not k1_doc.document:
            return Response(
                {'error': 'No PDF file associated with this document.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(
            k1_doc.document.open('rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=k1_doc.original_filename or f'k1_{k1_doc.id}.pdf',
        )

    # ---- Auto-populate portfolio (T054) ----

    @action(detail=True, methods=['post'], url_path='populate')
    def populate(self, request, pk=None):
        """Create Distribution records from a confirmed K-1 document."""
        from .k1_portfolio import populate_portfolio_from_k1

        k1_doc = self.get_object()
        try:
            result = populate_portfolio_from_k1(k1_doc)
            return Response({
                'message': (
                    f"Created {result['distributions_created']} distribution(s) "
                    f"totaling ${result['total_distributions']} and recorded "
                    f"{result['income_items_processed']} income item(s) in the "
                    f"Activity ledger."
                ),
                **result,
                'total_distributions': str(result['total_distributions']),
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ---- Simulate K-1 upload (dev / demo) ----

    @action(detail=False, methods=['post'], url_path='simulate')
    def simulate(self, request):
        """Generate realistic mock K-1 data for entity/asset pairs.

        Body params:
            year (int, required)  — Tax year to simulate.
            entity (int, optional) — Limit to one entity.
            asset  (int, optional) — Limit to one asset.

        For every qualifying ownership pair that does NOT already have a
        populated K-1 for that year, creates K1Document + child records,
        auto-confirms, and runs the populate pipeline so Distribution +
        Activity rows appear immediately.
        """
        from .k1_simulator import simulate_k1_batch

        year = request.data.get('year')
        if not year:
            return Response(
                {'error': 'year is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response(
                {'error': 'year must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entity_id = request.data.get('entity') or None
        asset_id = request.data.get('asset') or None

        try:
            result = simulate_k1_batch(year, entity_id=entity_id, asset_id=asset_id)
            n = len(result['created'])
            s = len(result['skipped'])
            return Response({
                'message': f"Simulated {n} K-1(s) for {year}. Skipped {s}.",
                **result,
            })
        except Exception as exc:
            logger.exception('K-1 simulation failed')
            return Response(
                {'error': f'Simulation failed: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
