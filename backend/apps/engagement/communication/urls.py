from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(
    "notifications/templates", views.NotificationTemplateViewSet, basename="notification-templates"
)
router.register("notifications/logs", views.NotificationLogViewSet, basename="notification-logs")

urlpatterns = [
    path("notifications/send/", views.NotificationSendView.as_view(), name="notifications-send"),
] + router.urls
