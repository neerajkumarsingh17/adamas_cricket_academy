from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("enquiries", views.EnquiryViewSet, basename="enquiries")

urlpatterns = [
    path("public/enquiries/", views.PublicEnquiryCreateView.as_view(), name="public-enquiries"),
] + router.urls
