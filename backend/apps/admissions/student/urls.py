from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("students", views.StudentViewSet, basename="students")

urlpatterns = [
    # docs/02-api-spec.md lists this under "Admissions" — see
    # views.AdmissionApproveView's docstring for why it's implemented (and
    # its URL registered) here in `student` instead.
    path(
        "admissions/<uuid:admission_id>/approve/",
        views.AdmissionApproveView.as_view(),
        name="admission-approve",
    ),
    # Explicit path, not router.register() — StudentProfileViewSet has its
    # own `module` (see its docstring) and defines only these two actions;
    # registering it as a second full ModelViewSet at the same "students"
    # prefix would generate colliding list/retrieve/etc. routes on top of
    # StudentViewSet's own.
    path(
        "students/<uuid:pk>/profile/",
        views.StudentProfileViewSet.as_view({"get": "profile", "patch": "profile_update"}),
        name="student-profile",
    ),
] + router.urls
