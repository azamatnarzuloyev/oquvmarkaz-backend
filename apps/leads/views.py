from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from shared.permissions import IsAdminOrReception
from .models import Lead, LeadActivity, LeadStatus, ActivityType
from .serializers import (
    LeadListSerializer, LeadDetailSerializer,
    LeadCreateSerializer, LeadUpdateSerializer,
    StatusChangeSerializer, LeadActivitySerializer,
)
from .filters import LeadFilter


class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrReception,)
    filterset_class    = LeadFilter
    search_fields      = ('full_name', 'phone', 'notes')
    ordering_fields    = ('created_at', 'updated_at', 'full_name')
    ordering           = ('-created_at',)

    def get_queryset(self):
        qs = Lead.objects.select_related('assigned_to').prefetch_related('activities')
        if self.request.user.role == 'reception':
            return qs.filter(assigned_to=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        if self.action == 'create':
            return LeadCreateSerializer
        if self.action in ('update', 'partial_update'):
            return LeadUpdateSerializer
        return LeadDetailSerializer

    def perform_create(self, serializer):
        lead = serializer.save(assigned_to=self.request.user if self.request.user.role == 'reception' else serializer.validated_data.get('assigned_to'))
        LeadActivity.objects.create(
            lead=lead,
            created_by=self.request.user,
            type=ActivityType.NOTE,
            content='Lid tizimga qo\'shildi',
        )

    @extend_schema(request=StatusChangeSerializer, responses={200: LeadDetailSerializer})
    @action(detail=True, methods=['patch'], url_path='change-status')
    def change_status(self, request, pk=None):
        lead = self.get_object()
        serializer = StatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = lead.get_status_display()
        lead.status = serializer.validated_data['status']

        if lead.status == LeadStatus.LOST:
            lead.lost_reason = serializer.validated_data.get('lost_reason', '')

        if lead.status == LeadStatus.TRIAL and serializer.validated_data.get('trial_date'):
            lead.trial_date = serializer.validated_data['trial_date']

        if lead.status == LeadStatus.CONVERTED:
            lead.converted_at = timezone.now()

        lead.save()

        LeadActivity.objects.create(
            lead=lead,
            created_by=request.user,
            type=ActivityType.STATUS_CHANGED,
            content=f'Holat o\'zgartirildi: {old_status} → {lead.get_status_display()}',
        )

        return Response({'success': True, 'data': LeadDetailSerializer(lead).data})

    @extend_schema(responses={200: LeadDetailSerializer})
    @action(detail=True, methods=['post'], url_path='convert')
    def convert(self, request, pk=None):
        lead = self.get_object()
        if lead.status == LeadStatus.CONVERTED:
            return Response(
                {'success': False, 'error': {'message': 'Lid allaqachon talabaga aylantirilgan'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lead.status       = LeadStatus.CONVERTED
        lead.converted_at = timezone.now()
        lead.save()

        LeadActivity.objects.create(
            lead=lead,
            created_by=request.user,
            type=ActivityType.STATUS_CHANGED,
            content='Talabaga aylantirildi',
        )

        return Response({'success': True, 'data': LeadDetailSerializer(lead).data})

    @extend_schema(
        parameters=[OpenApiParameter('lead_pk', location='path', required=True)],
        responses={200: LeadActivitySerializer(many=True)}
    )
    @action(detail=True, methods=['get', 'post'], url_path='activities')
    def activities(self, request, pk=None):
        lead = self.get_object()

        if request.method == 'GET':
            acts = lead.activities.select_related('created_by').all()
            return Response({'success': True, 'data': LeadActivitySerializer(acts, many=True).data})

        serializer = LeadActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = serializer.save(lead=lead, created_by=request.user)
        return Response({'success': True, 'data': LeadActivitySerializer(activity).data}, status=status.HTTP_201_CREATED)


class LeadStatsView(viewsets.ViewSet):
    permission_classes = (IsAdminOrReception,)

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=['get'], url_path='funnel')
    def funnel(self, request):
        from django.db.models import Count
        qs = Lead.objects.values('status').annotate(count=Count('id'))
        data = {item['status']: item['count'] for item in qs}

        total     = sum(data.values())
        converted = data.get('converted', 0)
        conversion_rate = round((converted / total * 100), 1) if total else 0

        return Response({
            'success': True,
            'data': {
                'by_status':       data,
                'total':           total,
                'conversion_rate': conversion_rate,
            }
        })

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from datetime import date, timedelta

        # By source
        by_source = {
            item['source']: item['count']
            for item in Lead.objects.values('source').annotate(count=Count('id'))
        }

        # Last 7 days new leads
        today = date.today()
        week_ago = today - timedelta(days=6)
        daily_qs = (
            Lead.objects
            .filter(created_at__date__gte=week_ago)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        daily_map = {item['day'].isoformat(): item['count'] for item in daily_qs}
        weekly = [
            {
                'date': (week_ago + timedelta(days=i)).isoformat(),
                'count': daily_map.get((week_ago + timedelta(days=i)).isoformat(), 0),
            }
            for i in range(7)
        ]

        # By status
        by_status = {
            item['status']: item['count']
            for item in Lead.objects.values('status').annotate(count=Count('id'))
        }
        total = sum(by_status.values())
        converted = by_status.get('converted', 0)

        return Response({
            'success': True,
            'data': {
                'by_source':       by_source,
                'weekly_new':      weekly,
                'by_status':       by_status,
                'total':           total,
                'conversion_rate': round(converted / total * 100, 1) if total else 0,
            }
        })
