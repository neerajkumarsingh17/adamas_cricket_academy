from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

from . import views

router = SimpleRouter()
router.register("iam/roles", views.RoleViewSet, basename="iam-roles")

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", TokenBlacklistView.as_view(), name="auth-logout"),
    path("auth/otp/request/", views.OTPRequestView.as_view(), name="auth-otp-request"),
    path("auth/otp/verify/", views.OTPVerifyView.as_view(), name="auth-otp-verify"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
] + router.urls
