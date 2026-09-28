from django.urls import path

from . import views

urlpatterns = [
    path("parents/me/children/", views.ParentChildrenListView.as_view(), name="parent-children"),
    path(
        "parents/me/children/<uuid:student_id>/",
        views.ParentChildDetailView.as_view(),
        name="parent-child-detail",
    ),
    path(
        "parents/me/children/<uuid:student_id>/payments/",
        views.ParentChildPaymentsView.as_view(),
        name="parent-child-payments",
    ),
    path(
        "parents/me/documents/",
        views.ParentDocumentUploadView.as_view(),
        name="parent-documents",
    ),
    path(
        "parents/me/settings/",
        views.ParentPortalSettingsView.as_view(),
        name="parent-settings",
    ),
]
