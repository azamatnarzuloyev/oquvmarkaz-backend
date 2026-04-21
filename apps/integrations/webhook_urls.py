from django.urls import path
from .views import WebhookReceiveView, WebhookStatUpdateView

urlpatterns = [
    path('<uuid:token>/',        WebhookReceiveView.as_view(),    name='webhook-receive'),
    path('<uuid:token>/stats/',  WebhookStatUpdateView.as_view(), name='webhook-stats'),
]
