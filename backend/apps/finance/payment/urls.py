from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

# /payments/online/ (list), /setup/, /checkout/, /send-link/, and
# /{id}/confirm|sync|resend-link|cancel-link/. No clash with the
# /payments/<uuid:pk>/... routes below — "online" is never a UUID.
router = SimpleRouter()
router.register("payments/online", views.OnlinePaymentViewSet, basename="online-payment")

urlpatterns = [
    path(
        "payments/gateway/<str:gateway>/webhook/",
        views.PaymentGatewayWebhookView.as_view(),
        name="payment-gateway-webhook",
    ),
    path("payments/", views.PaymentListView.as_view(), name="payment-list"),
    path("payments/record/", views.PaymentRecordView.as_view(), name="payment-record"),
    path("payments/current-fee/", views.CurrentFeeView.as_view(), name="payment-current-fee"),
    path("payments/<uuid:pk>/settle/", views.PaymentSettleView.as_view(), name="payment-settle"),
    path(
        "payments/<uuid:pk>/receipt.pdf/",
        views.PaymentReceiptPdfView.as_view(),
        name="payment-receipt-pdf",
    ),
    path(
        "payments/<uuid:pk>/invoice.pdf/",
        views.PaymentInvoicePdfView.as_view(),
        name="payment-invoice-pdf",
    ),
] + router.urls
