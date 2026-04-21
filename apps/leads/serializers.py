from rest_framework import serializers
from apps.users.serializers import UserSerializer
from .models import Lead, LeadActivity, LeadStatus


class LeadActivitySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model  = LeadActivity
        fields = ('id', 'type', 'content', 'created_by', 'created_by_name', 'created_at')
        read_only_fields = ('id', 'created_by', 'created_by_name', 'created_at')


class LeadListSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    source_display   = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model  = Lead
        fields = (
            'id', 'full_name', 'phone', 'source', 'source_display',
            'status', 'status_display', 'assigned_to', 'assigned_to_name',
            'trial_date', 'created_at', 'updated_at',
        )


class LeadDetailSerializer(serializers.ModelSerializer):
    assigned_to_detail = UserSerializer(source='assigned_to', read_only=True)
    status_display     = serializers.CharField(source='get_status_display', read_only=True)
    source_display     = serializers.CharField(source='get_source_display', read_only=True)
    activities         = LeadActivitySerializer(many=True, read_only=True)

    class Meta:
        model  = Lead
        fields = (
            'id', 'full_name', 'phone', 'source', 'source_display',
            'status', 'status_display', 'assigned_to', 'assigned_to_detail',
            'notes', 'trial_date', 'lost_reason', 'converted_at',
            'created_at', 'updated_at', 'activities',
        )
        read_only_fields = ('id', 'converted_at', 'created_at', 'updated_at')


class LeadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Lead
        fields = ('full_name', 'phone', 'source', 'assigned_to', 'notes', 'trial_date')

    def validate_phone(self, value):
        cleaned = value.strip().replace(' ', '')
        if not cleaned.startswith('+998') or len(cleaned) != 13:
            raise serializers.ValidationError("Telefon formati: +998XXXXXXXXX")
        return cleaned


class LeadUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Lead
        fields = ('full_name', 'phone', 'source', 'assigned_to', 'notes', 'trial_date', 'lost_reason')

    def validate_phone(self, value):
        cleaned = value.strip().replace(' ', '')
        if not cleaned.startswith('+998') or len(cleaned) != 13:
            raise serializers.ValidationError("Telefon formati: +998XXXXXXXXX")
        return cleaned


class StatusChangeSerializer(serializers.Serializer):
    status      = serializers.ChoiceField(choices=LeadStatus.choices)
    lost_reason = serializers.CharField(required=False, allow_blank=True)
    trial_date  = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get('status') == 'lost' and not attrs.get('lost_reason'):
            raise serializers.ValidationError({'lost_reason': "Yo'qotish sababi majburiy"})
        return attrs
