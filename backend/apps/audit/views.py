from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.views import ModuleScopedViewSet

from .filters import AuditLogFilter
from .models import AuditAction, AuditLog
from .serializers import AuditExportResponseSerializer, AuditLogSerializer


class AuditLogViewSet(ModuleScopedViewSet):
    """docs/02-api-spec.md — "No POST, PATCH or DELETE on individual log
    rows. Ever." `http_method_names` below makes every method but GET
    return 405 regardless of what the router wires up, and `AuditLog`'s own
    `_AppendOnlyQuerySet`/`save()`/`delete()` overrides mean even a bug that
    somehow reached a write path here would still refuse at the model layer.
    """

    module = "audit"
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related("actor").all()
    filterset_class = AuditLogFilter
    http_method_names = ["get", "head", "options"]


class AuditLogExportView(APIView):
    """POST /audit/logs/export — docs/02-api-spec.md: "The export is itself
    audited". Real async job dispatch + file generation is Phase 12's
    ExportJob/reporting engine (docs/04... effort table, Phase 12); this
    Phase 0 slice honours the one requirement Phase 1 actually needs from
    it — that an export write its own audit row with the filter and row
    count — without building the report-file pipeline early.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.has_perm_for("audit", "export"):
            self.permission_denied(request)

        queryset = AuditLogFilter(request.data, queryset=AuditLog.objects.all()).qs
        row_count = queryset.count()

        AuditLog.objects.create(
            actor=request.user,
            action=AuditAction.EXPORT,
            model_label="audit.AuditLog",
            object_id="bulk",
            changes={"filter": dict(request.data), "row_count": row_count},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            request_id=getattr(request, "request_id", ""),
        )

        return Response(
            AuditExportResponseSerializer({"status": "queued", "row_count": row_count}).data
        )
