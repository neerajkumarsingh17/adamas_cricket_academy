from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core.models import EnquirySource
from apps.core.views import ModuleScopedViewSet

from . import services
from .filters import EnquiryFilter
from .models import Enquiry
from .serializers import (
    ConversionAnalyticsRowSerializer,
    DuplicateCandidateSerializer,
    EnquiryFollowUpSerializer,
    EnquiryReadSerializer,
    EnquiryWriteSerializer,
)


class EnquiryViewSet(ModuleScopedViewSet):
    module = "enquiry"
    queryset = Enquiry.objects.select_related("person", "source", "owner").all()
    filterset_class = EnquiryFilter

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EnquiryWriteSerializer
        return EnquiryReadSerializer

    def filter_to_own(self, queryset):
        # No seeded role holds scope="own" on `enquiry` (docs/03-rbac.md),
        # but ModuleScopedViewSet requires every module to define what
        # "own" would mean if one ever did — the natural reading here is
        # "enquiries this user owns", i.e. is chasing.
        return queryset.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        """Overridden rather than layered on `perform_create` — the create
        response needs the *read* shape plus the duplicate-match payload
        T-407 needs, which the standard `CreateModelMixin` flow (serialize
        with the same write serializer used for input) can't produce.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry, match = services.create_enquiry(serializer.validated_data, owner=request.user)
        data = {
            **EnquiryReadSerializer(enquiry).data,
            "duplicate_candidates": DuplicateCandidateSerializer(
                {"exact": match.exact, "fuzzy": match.fuzzy}
            ).data,
        }
        return Response(data, status=201)

    @action(detail=True, methods=["post"], url_path="follow-ups", verb="add")
    def follow_ups(self, request, pk=None):
        enquiry = self.get_object()
        serializer = EnquiryFollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        follow_up = services.add_follow_up(
            enquiry, created_by=request.user, **serializer.validated_data
        )
        return Response(EnquiryFollowUpSerializer(follow_up).data, status=201)

    @action(detail=False, methods=["get"], url_path="analytics/conversion", verb="view")
    def analytics_conversion(self, request):
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")
        rows = services.conversion_analytics(date_from=date_from, date_to=date_to)
        return Response(ConversionAnalyticsRowSerializer(rows, many=True).data)


class PublicEnquiryThrottle(AnonRateThrottle):
    scope = "public_enquiry"


class PublicEnquiryCreateView(APIView):
    """POST /public/enquiries — docs/02-api-spec.md: **public**, rate-limited,
    captcha. Captcha verification is a specific third-party integration
    (reCAPTCHA/hCaptcha) with no vendor named anywhere in the docs — not
    guessed at here; `AnonRateThrottle` is the abuse control this slice
    actually implements. `owner` and `status` are never client-settable —
    a public submission always starts unowned and `new`.
    """

    permission_classes = []
    authentication_classes = []
    throttle_classes = [PublicEnquiryThrottle]

    def post(self, request):
        payload = {k: v for k, v in request.data.items() if k not in ("owner", "status", "source")}
        # `source` is a FK id an anonymous visitor has no authenticated way
        # to look up (GET /master/enquiry-sources requires login) — every
        # submission through this specific endpoint is, by definition, a
        # website lead, so it's set here rather than trusted from the
        # client (which would otherwise let a caller claim any source).
        try:
            payload["source"] = EnquirySource.objects.get(code="website").id
        except EnquirySource.DoesNotExist:
            raise ValidationError(
                {"detail": "No 'website' EnquirySource configured — run seed_master_data."}
            ) from None

        serializer = EnquiryWriteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        enquiry, _match = services.create_enquiry(serializer.validated_data, owner=None)

        from apps.engagement.communication.services import NoActiveTemplate
        from apps.engagement.communication.services import send as send_notification

        try:
            send_notification(
                code="enquiry_acknowledgement",
                recipient=enquiry.guardian_mobile,
                context={
                    "student_name": enquiry.student_name,
                    "enquiry_no": enquiry.enquiry_no,
                },
            )
        except NoActiveTemplate:
            pass

        return Response(EnquiryReadSerializer(enquiry).data, status=201)
