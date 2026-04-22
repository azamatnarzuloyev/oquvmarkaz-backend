from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from shared.permissions import IsAdminUser
from .models import User, UserRole
from .serializers import LoginSerializer, LogoutSerializer, UserSerializer, StaffSerializer


class LoginView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(request=LoginSerializer, responses={200: LoginSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response({'success': True, **serializer.validated_data}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response({'success': True, 'data': UserSerializer(request.user).data})


class StaffViewSet(viewsets.ModelViewSet):
    """Operatorlar (admin/reception/teacher) CRUD — faqat admin."""
    permission_classes = (IsAdminUser,)
    serializer_class   = StaffSerializer

    def get_queryset(self):
        return (
            User.objects
            .exclude(role=UserRole.STUDENT)
            .prefetch_related('assigned_leads')
            .order_by('-created_at')
        )

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'error': "O'zingizni bloklayolmaysiz"}, status=400)
        user.is_active = not user.is_active
        user.save()
        return Response({'success': True, 'is_active': user.is_active})

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get('password', '')
        if len(new_password) < 6:
            return Response({'error': "Parol kamida 6 belgidan iborat bo'lishi kerak"}, status=400)
        user.set_password(new_password)
        user.save()
        return Response({'success': True})
