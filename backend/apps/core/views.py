from typing import Protocol, cast

import redis
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AgeCategory,
    ApprovalRequest,
    AssessmentCriterion,
    Building,
    DocumentType,
    EnquirySource,
    PaymentType,
    Programme,
    Season,
    TrainingType,
    Venue,
)
from .serializers import (
    AgeCategorySerializer,
    ApprovalDecisionSerializer,
    ApprovalRequestSerializer,
    AssessmentCriterionSerializer,
    BuildingSerializer,
    DashboardSerializer,
    DocumentTypeSerializer,
    EnquirySourceSerializer,
    PaymentTypeSerializer,
    ProgrammeSerializer,
    SeasonSerializer,
    TrainingTypeSerializer,
    VenueSerializer,
)
from .services import approvals, dashboards


class _PermissionCheckable(Protocol):
    """The slice of apps.iam.User this module needs — a Protocol, not an
    import, so apps/core still imports nothing from apps/ (docs/00-project
    -structure.md). Structural typing lets mypy check callers without core
    knowing the concrete User class exists.
    """

    def has_perm_for(self, module: str, verb: str) -> bool: ...
    def scope_for(self, module: str, verb: str) -> str | None: ...


class ModuleScopedViewSet(viewsets.ModelViewSet):
    """Base every module ViewSet extends:

        class EnquiryViewSet(ModuleScopedViewSet):
            module = "enquiry"

    Maps the HTTP method to a permission verb (GET->view, POST->add,
    PUT/PATCH->edit, DELETE->edit), checks it via request.user.has_perm_for,
    and — for roles whose widest scope on this module+verb is "own" —
    filters the queryset via filter_to_own(), which subclasses must
    implement (docs/03-rbac.md rule 3: enforced at the queryset level).

    A custom @action declares its own verb explicitly, which DRF's router
    passes through as an init kwarg:

        @action(detail=True, methods=["post"], verb="approve")
        def approve(self, request, pk=None): ...
    """

    module: str = ""
    verb: str | None = None
    # Per-action module override — e.g. {"create": "batch_admin", "destroy":
    # "batch_admin"} on a ViewSet whose write actions need a narrower role
    # set than its own list/retrieve/custom-actions (docs/03-rbac.md's
    # "split the row" pattern, applied at the action level instead of the
    # whole-ViewSet level for the first time). Empty by default, so every
    # existing ViewSet is unaffected.
    action_modules: dict[str, str] = {}

    permission_classes = [IsAuthenticated]

    _METHOD_VERBS = {
        "GET": "view",
        "POST": "add",
        "PUT": "edit",
        "PATCH": "edit",
        "DELETE": "edit",
    }

    def get_required_verb(self) -> str:
        return self.verb or self._METHOD_VERBS.get(self.request.method or "", "view")

    def get_module(self) -> str:
        return self.action_modules.get(self.action, self.module)

    def check_permissions(self, request):
        super().check_permissions(request)
        user = cast(_PermissionCheckable, request.user)
        if not user.has_perm_for(self.get_module(), self.get_required_verb()):
            self.permission_denied(request)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = cast(_PermissionCheckable, self.request.user)
        if user.scope_for(self.get_module(), self.get_required_verb()) == "own":
            queryset = self.filter_to_own(queryset)
        return queryset

    def filter_to_own(self, queryset):
        """Restrict `queryset` to rows belonging to the current user.
        "Belonging to" means something different per model (Enquiry.owner,
        a student's own record via Person, ...), so every module ViewSet
        whose module has a scope="own" role must implement this.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement filter_to_own() to support scope='own'"
        )


class ProgrammeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only for now — docs/03-rbac.md has no "master" module row, so
    a permission-gated write endpoint isn't safely buildable without
    inventing RBAC policy (same gap as "idcard": flagged, not guessed at).
    Write access is Django admin only until that row exists. Any
    authenticated user can read master data — it's reference data nearly
    every role needs, not something to gate per-module.
    """

    queryset = Programme.objects.all()
    serializer_class = ProgrammeSerializer
    permission_classes = [IsAuthenticated]


class AgeCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgeCategory.objects.all()
    serializer_class = AgeCategorySerializer
    permission_classes = [IsAuthenticated]


class VenueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticated]


class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /master/buildings/ — populates the accommodation-assignment
    form's building picker (apps.admissions.student's
    StudentAccommodationViewSet). Read-only and ungated beyond
    IsAuthenticated, same reasoning as VenueViewSet/ProgrammeViewSet
    above: reference data, writable only through Django admin until a
    real RBAC row exists for managing the building list itself (distinct
    from `residential`, which governs *assigning* a student to one).
    """

    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated]


class SeasonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    permission_classes = [IsAuthenticated]


class EnquirySourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EnquirySource.objects.all()
    serializer_class = EnquirySourceSerializer
    permission_classes = [IsAuthenticated]


class TrainingTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TrainingType.objects.all()
    serializer_class = TrainingTypeSerializer
    permission_classes = [IsAuthenticated]


class DocumentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    permission_classes = [IsAuthenticated]


class PaymentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentType.objects.all()
    serializer_class = PaymentTypeSerializer
    permission_classes = [IsAuthenticated]


class AssessmentCriterionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssessmentCriterion.objects.all()
    serializer_class = AssessmentCriterionSerializer
    permission_classes = [IsAuthenticated]


class ApprovalListView(generics.ListAPIView):
    """GET /approvals — docs/02-api-spec.md: returns only requests this
    user may decide. Not a ModuleScopedViewSet: the module to check varies
    per row (it's on each request's rule), not fixed for the whole view.
    """

    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return approvals.decidable_by(self.request.user)


class _ApprovalDecisionView(APIView):
    permission_classes = [IsAuthenticated]
    approve: bool

    def post(self, request, pk=None):
        approval_request = get_object_or_404(ApprovalRequest, pk=pk)
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        approvals.decide(
            approval_request,
            request.user,
            approve=self.approve,
            reason=serializer.validated_data["reason"],
        )
        return Response(ApprovalRequestSerializer(approval_request).data)


class ApprovalApproveView(_ApprovalDecisionView):
    approve = True


class ApprovalRejectView(_ApprovalDecisionView):
    approve = False


class DashboardMeView(APIView):
    """GET /api/v1/dashboards/me — the dashboard for the CALLING user's
    role. No role parameter exists anywhere on this endpoint: the client
    cannot ask for another role's payload by changing anything in the
    request, because the role is resolved server-side from request.user.

    Not a ModuleScopedViewSet: docs/03-rbac.md has no "dashboard" module
    row (same documented gap as "idcard" and "master") — IsAuthenticated
    only, same precedent as the master-data ViewSets above.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=DashboardSerializer)
    def get(self, request):
        try:
            payload = dashboards.build_dashboard(request.user)
        except dashboards.NoDashboardForRole:
            raise NotFound("No dashboard is available for your role.") from None
        return Response(payload)


def _database_ok() -> bool:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except OperationalError:
        return False


def _redis_ok() -> bool:
    try:
        redis.from_url(settings.REDIS_URL, socket_connect_timeout=2).ping()
        return True
    except redis.RedisError:
        return False


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    database_ok = _database_ok()
    redis_ok = _redis_ok()
    payload = {
        "database": "ok" if database_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
    return Response(payload, status=200 if database_ok and redis_ok else 503)
