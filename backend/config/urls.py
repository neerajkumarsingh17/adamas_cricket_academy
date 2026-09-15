from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.iam.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.people.urls")),
    path("api/v1/", include("apps.engagement.communication.urls")),
    path("api/v1/", include("apps.admissions.enquiry.urls")),
    path("api/v1/", include("apps.admissions.trial.urls")),
    path("api/v1/", include("apps.admissions.admission.urls")),
    path("api/v1/", include("apps.admissions.student.urls")),
    path("api/v1/", include("apps.admissions.document.urls")),
    path("api/v1/", include("apps.admissions.idcard.urls")),
    path("api/v1/", include("apps.admissions.parent.urls")),
]
