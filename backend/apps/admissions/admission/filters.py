import django_filters

from .models import Admission


class AdmissionFilter(django_filters.FilterSet):
    class Meta:
        model = Admission
        fields = ["step", "programme"]
