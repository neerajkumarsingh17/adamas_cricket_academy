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
    path(
        "admissions/<uuid:pk>/online-payment/checkout/",
        views.AdmissionOnlinePaymentViewSet.as_view({"post": "checkout"}),
        name="admission-online-payment-checkout",
    ),
    path(
        "admissions/<uuid:pk>/online-payment/confirm/",
        views.AdmissionOnlinePaymentViewSet.as_view({"post": "confirm"}),
        name="admission-online-payment-confirm",
    ),
    path(
        "admissions/<uuid:pk>/online-payment/send-link/",
        views.AdmissionOnlinePaymentViewSet.as_view({"post": "send_link"}),
        name="admission-online-payment-send-link",
    ),
    path(
        "admissions/<uuid:pk>/online-payment/resend-link/",
        views.AdmissionOnlinePaymentViewSet.as_view({"post": "resend_link"}),
        name="admission-online-payment-resend-link",
    ),
    path(
        "admissions/<uuid:pk>/online-payment/cancel-link/",
        views.AdmissionOnlinePaymentViewSet.as_view({"post": "cancel_link"}),
        name="admission-online-payment-cancel-link",
    ),
    path(
        "admissions/<uuid:pk>/online-payment/sync/",
        views.AdmissionOnlinePaymentViewSet.as_view({"post": "sync"}),
        name="admission-online-payment-sync",
    ),
] + router.urls
