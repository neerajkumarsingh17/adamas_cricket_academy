import redis
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


class ModuleScopedViewSet(viewsets.ModelViewSet):
    """Base every module ViewSet extends:

        class EnquiryViewSet(ModuleScopedViewSet):
            module = "enquiry"

    Maps the HTTP method to a permission verb (GET->view, POST->add,
    PUT/PATCH->edit, DELETE->edit). A custom @action declares its own verb
    explicitly, which DRF's router passes through as an init kwarg:

        @action(detail=True, methods=["post"], verb="approve")
        def approve(self, request, pk=None): ...

    The permission check itself is a TODO stub until apps.iam exists
    (T-104) — see docs/06-conventions.md, the Permissions section.
    """

    module: str = ""
    verb: str | None = None

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

    def check_permissions(self, request):
        super().check_permissions(request)
        # TODO(T-104): once apps.iam exists —
        #   if not request.user.has_perm_for(self.module, self.get_required_verb()):
        #       self.permission_denied(request)


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
