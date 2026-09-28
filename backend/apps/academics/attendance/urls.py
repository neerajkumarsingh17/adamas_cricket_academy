from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("attendance", views.AttendanceViewSet, basename="attendance")
router.register("corrections", views.AttendanceCorrectionViewSet, basename="corrections")

urlpatterns = [
    # SessionAttendanceViewSet operates on apps.academics.batch's
    # TrainingSession — see that class's own docstring for why these
    # three live here, explicitly path()-wired (verb= passed directly,
    # not via @action — see the same docstring).
    path(
        "sessions/<uuid:pk>/roster/",
        views.SessionAttendanceViewSet.as_view({"get": "roster"}, verb="view"),
        name="session-roster",
    ),
    path(
        "sessions/<uuid:pk>/attendance/",
        views.SessionAttendanceViewSet.as_view({"post": "attendance"}, verb="add"),
        name="session-attendance",
    ),
    path(
        "sessions/<uuid:pk>/cancel/",
        views.SessionAttendanceViewSet.as_view({"post": "cancel"}, verb="edit"),
        name="session-cancel",
    ),
    path(
        "sessions/<uuid:pk>/mark-conducted/",
        views.SessionAttendanceViewSet.as_view({"post": "mark_conducted"}, verb="edit"),
        name="session-mark-conducted",
    ),
    path(
        "sessions/<uuid:pk>/update-details/",
        views.SessionAttendanceViewSet.as_view({"post": "update_details"}, verb="edit"),
        name="session-update-details",
    ),
    path(
        "sessions/<uuid:pk>/delete/",
        views.SessionAttendanceViewSet.as_view({"post": "delete_session"}, verb="edit"),
        name="session-delete",
    ),
    # Operates on Batch, registered here for the same dependency-direction
    # reason as the three session routes above — see BatchReportViewSet.
    path(
        "batches/<uuid:pk>/attendance-report/",
        views.BatchReportViewSet.as_view({"get": "attendance_report"}, verb="view"),
        name="batch-attendance-report",
    ),
] + router.urls
