from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("audit/logs", views.AuditLogViewSet, basename="audit-logs")

urlpatterns = [
    path("audit/logs/export/", views.AuditLogExportView.as_view(), name="audit-logs-export"),
] + router.urls
