from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .admin_views import AdminUserViewSet, VerifyAdminPasswordView
from .views import (
    RegisterView, VerifyEmailView, ResendVerificationView,
    Enable2FAView, Disable2FAView, LoginView, WalletLoginView, SendOTPEmailView,
    UserProfileView
)

router = DefaultRouter()
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('wallet-login/', WalletLoginView.as_view(), name='wallet-login'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('2fa/enable/', Enable2FAView.as_view(), name='enable-2fa'),
    path('2fa/disable/', Disable2FAView.as_view(), name='disable-2fa'),
    path('2fa/send-otp/', SendOTPEmailView.as_view(), name='send-otp'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('verify-admin-password/', VerifyAdminPasswordView.as_view(), name='verify-admin-password'),
]
