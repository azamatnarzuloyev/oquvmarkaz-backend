from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebhookTokenViewSet, InstagramActivityListView

router = DefaultRouter()
router.register('tokens', WebhookTokenViewSet, basename='webhook-token')

urlpatterns = [
    path('', include(router.urls)),
    path('instagram/activity/', InstagramActivityListView.as_view(), name='instagram-activity'),
]
