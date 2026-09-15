from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.people.serializers import PersonSerializer

from .models import Role


class LoginSerializer(TokenObtainPairSerializer):
    """POST /auth/login — {login_id, password} -> access + refresh.

    TokenObtainPairSerializer already keys the username field off
    User.USERNAME_FIELD dynamically, so "login_id" just works. The only
    addition here is stamping last_login_at (docs/01-data-model.md), which
    simplejwt's own UPDATE_LAST_LOGIN only ever does for the built-in
    AbstractBaseUser.last_login field, not this one.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        assert self.user is not None  # set by super().validate() on success
        self.user.last_login_at = timezone.now()
        self.user.save(update_fields=["last_login_at"])
        return data


class OTPRequestSerializer(serializers.Serializer):
    mobile = serializers.CharField()


class OTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField()
    otp = serializers.RegexField(r"^\d{6}$")


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "code", "name", "description", "is_system"]


# Response-only shapes (docs/06-conventions.md: "one serializer per read
# shape") for the plain APIViews in views.py, which otherwise have no
# introspectable response schema — needed for `npm run generate:api` to
# produce accurate types for anything the frontend actually renders.


class TokenPairSerializer(serializers.Serializer):
    """POST /auth/login, POST /auth/otp/verify response shape."""

    access = serializers.CharField()
    refresh = serializers.CharField()


class OTPRequestResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    expires_in = serializers.IntegerField()


class RoleSummarySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


class PermissionSummarySerializer(serializers.Serializer):
    module = serializers.CharField()
    verb = serializers.CharField()
    scope = serializers.CharField()


class MeSerializer(serializers.Serializer):
    id = serializers.CharField()
    login_id = serializers.CharField()
    person = PersonSerializer(allow_null=True)
    roles = RoleSummarySerializer(many=True)
    permissions = PermissionSummarySerializer(many=True)
