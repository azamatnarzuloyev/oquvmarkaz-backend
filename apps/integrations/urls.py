from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebhookTokenViewSet

router = DefaultRouter()
router.register('tokens', WebhookTokenViewSet, basename='webhook-token')

urlpatterns = [
    path('', include(router.urls)),
]
