from typing import cast

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admissions.student.models import Student
from apps.core.views import ModuleScopedViewSet
from apps.iam.models import User

from . import services
from .models import IDCard
from .pdf import render_batch_pdf, render_card_pdf
from .serializers import (
    BatchPrintSerializer,
    IDCardSerializer,
    IssueCardSerializer,
    QRResolveSerializer,
)


class IDCardViewSet(ModuleScopedViewSet):
    module = "idcard"
    serializer_class = IDCardSerializer
    queryset = IDCard.objects.select_related(
        "student", "student__person", "student__programme"
    ).all()
    http_method_names = ["get", "head", "options"]

    def filter_to_own(self, queryset):
        from apps.people.models import StudentGuardian

        user = cast(User, self.request.user)
        if user.person_id is None:
            return queryset.none()
        own_student_ids = set(
            Student.objects.filter(person=user.person).values_list("id", flat=True)
        )
        own_student_ids |= set(
            StudentGuardian.objects.filter(guardian__person=user.person).values_list(
                "student_id", flat=True
            )
        )
        return queryset.filter(student_id__in=own_student_ids)

    @action(detail=True, methods=["get"], url_path="render.pdf")
    def render_pdf(self, request, pk=None):
        """No explicit `verb` — defaults to GET's "view" (`_METHOD_VERBS`),
        same as `retrieve()`. A single card's PDF is something anyone who
        can already *see* that card (Administration/Academy Head/IT Admin
        with scope="all", or the Student/Parent it belongs to with
        scope="own" — docs/03-rbac.md's matrix) should be able to open,
        not an admin-only action. `print` stays reserved for `batch_print`
        below, a genuinely bulk/operational action — see docs/03-rbac.md's
        "Print — a verb the letter-grid can't express" section.
        """
        card = self.get_object()
        pdf_bytes = render_card_pdf(card)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{card.card_no}.pdf"'
        return response

    @action(detail=False, methods=["post"], url_path="batch-print", verb="print")
    def batch_print(self, request):
        serializer = BatchPrintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cards = self.get_queryset().filter(
            student_id__in=serializer.validated_data["student_ids"], status="active"
        )
        pdf_bytes = render_batch_pdf(cards)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="id-cards-batch.pdf"'
        return response


class IssueIDCardView(APIView):
    """POST /students/{id}/id-card — docs/02-api-spec.md lists this under
    "ID cards" but path-scoped under `/students/`. Implemented in
    `apps.admissions.idcard` (importing `Student` forward, which
    docs/00-project-structure.md's dependency chain allows — `idcard` hangs
    off `student`), registered from this app's urls.py.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, student_id):
        if not request.user.has_perm_for("idcard", "add"):
            self.permission_denied(request)
        student = get_object_or_404(Student, pk=student_id)
        serializer = IssueCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        card = services.issue_card(
            student,
            issued_by=request.user,
            valid_until=serializer.validated_data.get("valid_until"),
        )
        return Response(IDCardSerializer(card).data, status=201)


class QRResolveView(APIView):
    """GET /id-cards/resolve/{token} — docs/02-api-spec.md: "Unauthenticated
    returns validity only." `AllowAny` deliberately — the endpoint itself
    is public; `resolve_qr()` decides how much detail to return based on
    whether the (possibly anonymous) caller holds `idcard`/`view`.
    """

    permission_classes = [AllowAny]

    def get(self, request, token):
        authorized = bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm_for("idcard", "view")
        )
        result = services.resolve_qr(token, authorized=authorized)
        return Response(QRResolveSerializer(result).data)
