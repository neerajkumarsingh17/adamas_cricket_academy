from django.contrib import admin

from .models import ParentPortalAccess


@admin.register(ParentPortalAccess)
class ParentPortalAccessAdmin(admin.ModelAdmin):
    list_display = ["guardian", "is_portal_enabled", "preferred_language"]
    list_filter = ["is_portal_enabled", "preferred_language"]
    search_fields = ["guardian__person__first_name", "guardian__person__last_name"]
    autocomplete_fields = ["guardian"]
