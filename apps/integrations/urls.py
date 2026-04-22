from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebhookTokenViewSet, InstagramActivityListView, TelegramActivityListView, TelegramSetupView

router = DefaultRouter()
router.register('tokens', WebhookTokenViewSet, basename='webhook-token')

urlpatterns = [
    path('', include(router.urls)),
    path('instagram/activity/',  InstagramActivityListView.as_view(), name='instagram-activity'),
    path('telegram/activity/',   TelegramActivityListView.as_view(),  name='telegram-activity'),
    path('telegram/setup/',      TelegramSetupView.as_view(),         name='telegram-setup'),
]
