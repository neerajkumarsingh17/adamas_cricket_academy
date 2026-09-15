import django_filters

from .models import Document


class DocumentFilter(django_filters.FilterSet):
    # Lets a caller ask for one owner's documents specifically — e.g. the
    # parent portal's child detail page, where a parent with more than one
    # child must not see all of them mixed into a single list.
    owner_object_id = django_filters.UUIDFilter(field_name="owner_object_id")

    class Meta:
        model = Document
        fields = ["status", "document_type", "owner_object_id"]
