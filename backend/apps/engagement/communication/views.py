from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.views import ModuleScopedViewSet

from . import services
from .models import NotificationLog, NotificationTemplate
from .serializers import (
    NotificationLogSerializer,
    NotificationSendSerializer,
    NotificationTemplateSerializer,
)


class NotificationTemplateViewSet(ModuleScopedViewSet):
    module = "communication"
    serializer_class = NotificationTemplateSerializer
    queryset = NotificationTemplate.objects.all()
    http_method_names = ["get", "post", "patch", "head", "options"]


class NotificationLogViewSet(ModuleScopedViewSet):
    module = "communication"
    serializer_class = NotificationLogSerializer
    queryset = NotificationLog.objects.select_related("template").all()
    http_method_names = ["get", "head", "options"]


class NotificationSendView(APIView):
    """POST /notifications/send — docs/02-api-spec.md: one call fans out to
    every recipient. Not a ModuleScopedViewSet action since it isn't
    CRUD on a single resource.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.has_perm_for("communication", "add"):
            self.permission_denied(request)

        serializer = NotificationSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        logs = [
            services.send(
                code=serializer.validated_data["template_code"],
                recipient=recipient,
                context=serializer.validated_data.get("context", {}),
            )
            for recipient in serializer.validated_data["recipients"]
        ]
        return Response(NotificationLogSerializer(logs, many=True).data, status=202)
