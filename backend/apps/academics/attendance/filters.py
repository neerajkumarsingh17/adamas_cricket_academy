import django_filters

from .models import AttendanceCorrection


class AttendanceCorrectionFilter(django_filters.FilterSet):
    class Meta:
        model = AttendanceCorrection
        fields = ["status"]
