from django.contrib import admin

from .models import IDCard


@admin.register(IDCard)
class IDCardAdmin(admin.ModelAdmin):
    list_display = ["card_no", "student", "status", "issued_on", "valid_until"]
    list_filter = ["status"]
    search_fields = ["card_no", "student__student_code"]
    autocomplete_fields = ["student", "replaces", "issued_by"]
