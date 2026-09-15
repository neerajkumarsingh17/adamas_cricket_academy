import django_filters

from .models import AuditLog


class AuditLogFilter(django_filters.FilterSet):
    from_ = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    to = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = {
            "model_label": ["exact"],
            "object_id": ["exact"],
            "actor": ["exact"],
            "action": ["exact"],
        }

    def __init__(self, data=None, *args, **kwargs):
        # "from" is a Python keyword — accept it as a query param even
        # though the FilterSet field itself must be named "from_".
        if data is not None and "from" in data:
            data = data.copy()
            data["from_"] = data["from"]
        super().__init__(data, *args, **kwargs)
