from django.urls import path

from . import views

urlpatterns = [
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
]
