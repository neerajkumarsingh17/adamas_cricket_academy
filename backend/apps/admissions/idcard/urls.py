from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("id-cards", views.IDCardViewSet, basename="id-cards")

urlpatterns = [
    path(
        "students/<uuid:student_id>/id-card/",
        views.IssueIDCardView.as_view(),
        name="student-issue-id-card",
    ),
    path("id-cards/resolve/<str:token>/", views.QRResolveView.as_view(), name="id-card-resolve"),
] + router.urls
