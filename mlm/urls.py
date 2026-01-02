from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MLMViewSet
from .stats_views import StatsViewSet

router = DefaultRouter()
router.register(r'program', MLMViewSet, basename='mlm')
router.register(r'stats', StatsViewSet, basename='stats')

urlpatterns = [
    path('', include(router.urls)),
]
