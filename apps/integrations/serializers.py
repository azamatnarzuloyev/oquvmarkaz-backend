from rest_framework import serializers
from .models import WebhookToken, AdStat


class WebhookTokenSerializer(serializers.ModelSerializer):
    leads_count = serializers.SerializerMethodField()
    total_impressions = serializers.SerializerMethodField()
    total_clicks = serializers.SerializerMethodField()
    webhook_url = serializers.SerializerMethodField()

    class Meta:
        model  = WebhookToken
        fields = [
            'id', 'name', 'platform', 'token', 'is_active',
            'webhook_url', 'leads_count', 'total_impressions', 'total_clicks',
            'created_at',
        ]
        read_only_fields = ['id', 'token', 'created_at']

    def get_leads_count(self, obj):
        return obj.leads.count()

    def get_total_impressions(self, obj):
        return sum(obj.stats.values_list('impressions', flat=True))

    def get_total_clicks(self, obj):
        return sum(obj.stats.values_list('clicks', flat=True))

    def get_webhook_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/webhooks/{obj.token}/')
        return f'/api/webhooks/{obj.token}/'


class AdStatSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AdStat
        fields = ['id', 'date', 'impressions', 'clicks']


class WebhookLeadPayloadSerializer(serializers.Serializer):
    """Tashqi reklama platformasidan keluvchi lead ma'lumotlari."""
    full_name = serializers.CharField(max_length=100)
    phone     = serializers.CharField(max_length=20)
    notes     = serializers.CharField(required=False, allow_blank=True, default='')


class WebhookStatPayloadSerializer(serializers.Serializer):
    """Kunlik impressions va clicks yangilash."""
    date        = serializers.DateField()
    impressions = serializers.IntegerField(min_value=0, default=0)
    clicks      = serializers.IntegerField(min_value=0, default=0)
