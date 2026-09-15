from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("admissions", views.AdmissionViewSet, basename="admissions")

# POST /admissions/{id}/approve/ is registered from apps.admissions.student
# — see that app's services.py docstring for why.
urlpatterns = [
    path(
        "admissions/<uuid:pk>/record-payment/",
        views.AdmissionRecordPaymentView.as_view(),
        name="admission-record-payment",
    ),
    path(
        "admissions/<uuid:pk>/verify-payment/",
        views.AdmissionPaymentVerificationViewSet.as_view({"post": "verify"}),
        name="admission-verify-payment",
    ),
    path(
        "admissions/<uuid:pk>/verify-documents/",
        views.AdmissionDocumentVerificationViewSet.as_view({"post": "verify"}),
        name="admission-verify-documents",
    ),
] + router.urls
