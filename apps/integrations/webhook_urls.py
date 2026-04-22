from django.urls import path
from .views import WebhookReceiveView, WebhookStatUpdateView
from .instagram_webhook import InstagramWebhookView
from .telegram_bot import TelegramWebhookView

urlpatterns = [
    path('<uuid:token>/',        WebhookReceiveView.as_view(),    name='webhook-receive'),
    path('<uuid:token>/stats/',  WebhookStatUpdateView.as_view(), name='webhook-stats'),
    path('instagram/',           InstagramWebhookView.as_view(),  name='webhook-instagram'),
    path('telegram/',            TelegramWebhookView.as_view(),   name='webhook-telegram'),
]
