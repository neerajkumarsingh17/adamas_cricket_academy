from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("master/programmes", views.ProgrammeViewSet, basename="master-programmes")
router.register("master/age-categories", views.AgeCategoryViewSet, basename="master-age-categories")
router.register("master/venues", views.VenueViewSet, basename="master-venues")
router.register("master/buildings", views.BuildingViewSet, basename="master-buildings")
router.register("master/seasons", views.SeasonViewSet, basename="master-seasons")
router.register(
    "master/enquiry-sources", views.EnquirySourceViewSet, basename="master-enquiry-sources"
)
router.register(
    "master/training-types", views.TrainingTypeViewSet, basename="master-training-types"
)
router.register(
    "master/document-types", views.DocumentTypeViewSet, basename="master-document-types"
)
router.register(
    "master/assessment-criteria",
    views.AssessmentCriterionViewSet,
    basename="master-assessment-criteria",
)
router.register(
    "master/payment-types", views.PaymentTypeViewSet, basename="master-payment-types"
)

urlpatterns = [
    path("health/", views.health, name="health"),
    path("dashboards/me/", views.DashboardMeView.as_view(), name="dashboard-me"),
    path("approvals/", views.ApprovalListView.as_view(), name="approvals-list"),
    path(
        "approvals/<uuid:pk>/approve/",
        views.ApprovalApproveView.as_view(),
        name="approvals-approve",
    ),
    path(
        "approvals/<uuid:pk>/reject/", views.ApprovalRejectView.as_view(), name="approvals-reject"
    ),
] + router.urls
