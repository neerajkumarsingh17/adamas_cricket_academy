import django_filters
from django.db.models import Q

from .models import Enquiry


class EnquiryFilter(django_filters.FilterSet):
    """docs/02-api-spec.md: "Filters: status, source, owner, from, to,
    search". `django-filter`, declared explicitly — never raw
    `.filter(**request.query_params)` (docs/06-conventions.md).
    """

    from_ = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Enquiry
        fields = ["status", "source", "owner"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(student_name__icontains=value)
            | Q(guardian_name__icontains=value)
            | Q(guardian_mobile__icontains=value)
            | Q(enquiry_no__icontains=value)
        )

    def __init__(self, data=None, *args, **kwargs):
        if data is not None and "from" in data:
            data = data.copy()
            data["from_"] = data["from"]
        super().__init__(data, *args, **kwargs)
