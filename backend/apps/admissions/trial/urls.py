from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("trials/slots", views.TrialSlotViewSet, basename="trial-slots")
router.register(
    "trials/registrations", views.TrialRegistrationViewSet, basename="trial-registrations"
)

urlpatterns = [
    # docs/02-api-spec.md lists this under "Enquiry" — see
    # views.EnquiryConvertToTrialView's docstring for why it's implemented
    # (and its URL registered) here in `trial` instead.
    path(
        "enquiries/<uuid:enquiry_id>/convert-to-trial/",
        views.EnquiryConvertToTrialView.as_view(),
        name="enquiry-convert-to-trial",
    ),
    path(
        "trials/results/bulk-notify/",
        views.TrialBulkNotifyView.as_view(),
        name="trial-results-bulk-notify",
    ),
] + router.urls
