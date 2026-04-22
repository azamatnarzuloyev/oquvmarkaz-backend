from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, UserRole


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'phone', 'first_name', 'last_name', 'full_name', 'role', 'avatar', 'is_active')
        read_only_fields = ('id', 'created_at')


class LoginSerializer(serializers.Serializer):
    phone    = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone    = attrs.get('phone')
        password = attrs.get('password')

        user = authenticate(request=self.context.get('request'), username=phone, password=password)

        if not user:
            raise serializers.ValidationError('Telefon yoki parol noto\'g\'ri')

        if not user.is_active:
            raise serializers.ValidationError('Foydalanuvchi bloklangan')

        refresh = RefreshToken.for_user(user)
        return {
            'user': UserSerializer(user).data,
            'tokens': {
                'access':  str(refresh.access_token),
                'refresh': str(refresh),
            }
        }


class StaffSerializer(serializers.ModelSerializer):
    """Operator/xodim yaratish va tahrirlash uchun."""
    password   = serializers.CharField(write_only=True, required=False, min_length=6)
    full_name  = serializers.CharField(read_only=True)
    leads_count = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = (
            'id', 'phone', 'first_name', 'last_name', 'full_name',
            'role', 'avatar', 'is_active', 'password', 'leads_count', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_leads_count(self, obj):
        return obj.assigned_leads.count()

    def validate_role(self, value):
        if value == UserRole.STUDENT:
            raise serializers.ValidationError("Talaba roli bu yerda ishlatilmaydi")
        return value

    def validate_phone(self, value):
        qs = User.objects.filter(phone=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatda bor")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.is_staff = validated_data.get('role') == UserRole.ADMIN
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.is_staff = instance.role == UserRole.ADMIN
        instance.save()
        return instance


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except Exception:
            raise serializers.ValidationError('Token yaroqsiz yoki allaqachon bekor qilingan')
