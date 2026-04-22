from datetime import date, timedelta
from django.db.models import Sum, Count
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from shared.permissions import IsAdminOrReception
from .models import WebhookToken, AdStat, InstagramActivity
from .serializers import (
    WebhookTokenSerializer, AdStatSerializer,
    WebhookLeadPayloadSerializer, WebhookStatPayloadSerializer,
    InstagramActivitySerializer,
)


class WebhookTokenViewSet(viewsets.ModelViewSet):
    """Token boshqaruvi — admin/reception uchun."""
    permission_classes = (IsAdminOrReception,)
    serializer_class   = WebhookTokenSerializer

    def get_queryset(self):
        return WebhookToken.objects.prefetch_related('stats', 'leads').all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        token = self.get_object()
        # Last 30 days
        today    = date.today()
        from_date = today - timedelta(days=29)
        daily = (
            AdStat.objects
            .filter(webhook=token, date__gte=from_date)
            .values('date', 'impressions', 'clicks')
            .order_by('date')
        )
        # Fill missing days with 0
        daily_map = {str(r['date']): r for r in daily}
        result = []
        for i in range(30):
            d = from_date + timedelta(days=i)
            key = str(d)
            result.append({
                'date':        key,
                'impressions': daily_map.get(key, {}).get('impressions', 0),
                'clicks':      daily_map.get(key, {}).get('clicks', 0),
                'leads':       0,  # filled below
            })
        # Count leads per day
        leads_by_day = (
            token.leads
            .filter(created_at__date__gte=from_date)
            .extra(select={'day': 'date(created_at)'})
            .values('day')
            .annotate(cnt=Count('id'))
        )
        leads_map = {str(r['day']): r['cnt'] for r in leads_by_day}
        for row in result:
            row['leads'] = leads_map.get(row['date'], 0)

        return Response({'success': True, 'data': result})

    @action(detail=False, methods=['get'], url_path='overview')
    def overview(self, request):
        """Barcha tokenlar bo'yicha umumiy statistika."""
        tokens = self.get_queryset()
        data = []
        for t in tokens:
            agg = t.stats.aggregate(
                total_impressions=Sum('impressions'),
                total_clicks=Sum('clicks'),
            )
            leads = t.leads.count()
            impr  = agg['total_impressions'] or 0
            clicks = agg['total_clicks'] or 0
            ctr = round(clicks / impr * 100, 2) if impr else 0
            cpl = round(clicks / leads, 1) if leads else 0

            data.append({
                'id':          t.id,
                'name':        t.name,
                'platform':    t.platform,
                'is_active':   t.is_active,
                'impressions': impr,
                'clicks':      clicks,
                'leads':       leads,
                'ctr':         ctr,
                'cpl':         cpl,
                'created_at':  t.created_at,
            })

        total_impr   = sum(d['impressions'] for d in data)
        total_clicks = sum(d['clicks'] for d in data)
        total_leads  = sum(d['leads'] for d in data)

        return Response({
            'success': True,
            'data': {
                'tokens':          data,
                'total_impressions': total_impr,
                'total_clicks':     total_clicks,
                'total_leads':      total_leads,
                'avg_ctr':          round(total_clicks / total_impr * 100, 2) if total_impr else 0,
            }
        })


class WebhookReceiveView(APIView):
    """
    Tashqi reklama platformasidan lead qabul qilish.
    Autentifikatsiya talab qilinmaydi — token URL da.
    """
    permission_classes = (AllowAny,)

    def post(self, request, token):
        try:
            wt = WebhookToken.objects.get(token=token, is_active=True)
        except WebhookToken.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Webhook token topilmadi yoki faol emas'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WebhookLeadPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.leads.models import Lead, LeadSource, LeadActivity, ActivityType

        # Platform → LeadSource mapping
        platform_map = {
            'instagram': LeadSource.INSTAGRAM,
            'telegram':  LeadSource.TELEGRAM,
            'facebook':  LeadSource.INSTAGRAM,
            'website':   LeadSource.WEBSITE,
            'other':     LeadSource.OTHER,
        }
        lead_source = platform_map.get(wt.platform, LeadSource.OTHER)

        lead = Lead.objects.create(
            full_name     = serializer.validated_data['full_name'],
            phone         = serializer.validated_data['phone'],
            notes         = serializer.validated_data.get('notes', ''),
            source        = lead_source,
            webhook_token = wt,
        )

        LeadActivity.objects.create(
            lead       = lead,
            created_by = None,
            type       = ActivityType.NOTE,
            content    = f"Webhook orqali qo'shildi: {wt.name}",
        )

        return Response(
            {'success': True, 'data': {'lead_id': lead.id}},
            status=status.HTTP_201_CREATED,
        )


class WebhookStatUpdateView(APIView):
    """
    Kunlik impressions/clicks yangilash.
    Token URL da o'tkaziladi, autentifikatsiya yo'q.
    """
    permission_classes = (AllowAny,)

    def post(self, request, token):
        try:
            wt = WebhookToken.objects.get(token=token, is_active=True)
        except WebhookToken.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Token topilmadi'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WebhookStatPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stat, _ = AdStat.objects.get_or_create(
            webhook=wt,
            date=serializer.validated_data['date'],
        )
        stat.impressions += serializer.validated_data['impressions']
        stat.clicks      += serializer.validated_data['clicks']
        stat.save()

        return Response({'success': True})


class InstagramActivityListView(generics.ListAPIView):
    """Instagram comment/DM faoliyat logi."""
    permission_classes = (IsAdminOrReception,)
    serializer_class   = InstagramActivitySerializer

    def get_queryset(self):
        qs = InstagramActivity.objects.select_related('lead').all()
        event_type = self.request.query_params.get('event_type')
        if event_type:
            qs = qs.filter(event_type=event_type)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs
