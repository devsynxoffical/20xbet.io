from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WalletViewSet, TransactionViewSet, SystemSettingsView
from .admin_views import AdminTransactionViewSet

router = DefaultRouter()
router.register(r'wallet', WalletViewSet, basename='wallet')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'admin/transactions', AdminTransactionViewSet, basename='admin-transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('settings/', SystemSettingsView.as_view(), name='system-settings'),
]
