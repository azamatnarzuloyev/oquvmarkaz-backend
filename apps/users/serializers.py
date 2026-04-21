from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User


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
