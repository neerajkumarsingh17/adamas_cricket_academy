import django_filters

from .models import BatchEnrollment, TrainingSession


class BatchEnrollmentFilter(django_filters.FilterSet):
    # The batch roster screen asks for "this batch's active enrolments"
    # — without a batch filter GET /enrollments/ is every enrolment in
    # the academy, which is never what a roster wants.
    class Meta:
        model = BatchEnrollment
        fields = ["batch", "is_active"]


class TrainingSessionFilter(django_filters.FilterSet):
    class Meta:
        model = TrainingSession
        fields = ["date", "batch"]
