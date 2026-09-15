from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.views import ModuleScopedViewSet
from apps.people.serializers import PersonSerializer
from apps.people.services import normalize_mobile_e164

from .models import Role, User
from .serializers import (
    LoginSerializer,
    MeSerializer,
    OTPRequestResponseSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    RoleSerializer,
    TokenPairSerializer,
)
from .services import generate_and_store_otp, send_otp_sms, verify_otp


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

    @extend_schema(responses=TokenPairSerializer)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class OTPRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=OTPRequestSerializer, responses=OTPRequestResponseSerializer)
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = normalize_mobile_e164(serializer.validated_data["mobile"])

        otp = generate_and_store_otp(mobile)
        send_otp_sms(mobile, otp)

        return Response({"detail": "OTP sent.", "expires_in": 600})


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=OTPVerifySerializer, responses=TokenPairSerializer)
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = normalize_mobile_e164(serializer.validated_data["mobile"])
        otp = serializer.validated_data["otp"]

        if not verify_otp(mobile, otp):
            raise AuthenticationFailed("Invalid or expired OTP.")

        user = self._find_user_by_mobile(mobile)
        if user is None:
            # Same message as an invalid code — don't confirm whether an
            # account exists for this number.
            raise AuthenticationFailed("Invalid or expired OTP.")

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])

        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})

    @staticmethod
    def _find_user_by_mobile(mobile: str) -> User | None:
        candidates = list(User.objects.filter(person__mobile=mobile, is_active=True))
        if len(candidates) != 1:
            return None
        return candidates[0]


class RoleViewSet(ModuleScopedViewSet):
    """GET /iam/roles — docs/02-api-spec.md. Read-only: roles are seed data
    (seed_roles), never created/edited through the API.
    """

    module = "iam"
    serializer_class = RoleSerializer
    queryset = Role.objects.all()
    http_method_names = ["get", "head", "options"]


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        user = request.user
        return Response(
            {
                "id": str(user.id),
                "login_id": user.login_id,
                "person": PersonSerializer(user.person).data if user.person else None,
                "roles": [{"code": role.code, "name": role.name} for role in user.current_roles()],
                "permissions": [
                    {"module": module, "verb": verb, "scope": scope}
                    for (module, verb), scope in user.resolved_permissions().items()
                ],
            }
        )
