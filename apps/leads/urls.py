from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeadViewSet, LeadStatsView

router = DefaultRouter()
router.register('', LeadViewSet, basename='lead')
router.register('stats', LeadStatsView, basename='lead-stats')

urlpatterns = [
    path('', include(router.urls)),
]
