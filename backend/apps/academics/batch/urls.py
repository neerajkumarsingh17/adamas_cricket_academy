from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("batches", views.BatchViewSet, basename="batches")
router.register("enrollments", views.BatchEnrollmentViewSet, basename="enrollments")
router.register("sessions", views.TrainingSessionViewSet, basename="sessions")
router.register("coaches", views.CoachViewSet, basename="coaches")

urlpatterns = router.urls
