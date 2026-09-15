import django_filters

from .models import TrialRegistration, TrialSlot


class TrialSlotFilter(django_filters.FilterSet):
    class Meta:
        model = TrialSlot
        fields = ["date", "venue", "age_category"]


class TrialRegistrationFilter(django_filters.FilterSet):
    """docs/02-api-spec.md: "Filters: slot, date, outcome"."""

    date = django_filters.DateFilter(field_name="slot__date")
    outcome = django_filters.CharFilter(field_name="result__outcome")

    class Meta:
        model = TrialRegistration
        fields = ["slot", "date", "outcome"]
