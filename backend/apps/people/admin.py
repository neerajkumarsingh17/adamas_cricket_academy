from django.contrib import admin

from .models import Guardian, Person, Staff, StudentGuardian


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "date_of_birth", "gender", "mobile"]
    list_filter = ["gender", "blood_group"]
    search_fields = ["first_name", "last_name", "mobile", "email"]
    # dedupe_key is computed on save (SOP §78) — never hand-editable.
    readonly_fields = ["dedupe_key"]


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ["person", "occupation", "portal_access"]
    list_filter = ["portal_access"]
    search_fields = ["person__first_name", "person__last_name", "person__mobile"]
    autocomplete_fields = ["person"]


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    list_display = ["student", "guardian", "relationship", "is_primary", "is_emergency_contact"]
    list_filter = ["relationship", "is_primary", "is_emergency_contact"]
    search_fields = [
        "guardian__person__first_name",
        "guardian__person__last_name",
        "student__id",
    ]
    autocomplete_fields = ["guardian", "student"]


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ["person", "employee_code", "staff_type", "is_active"]
    list_filter = ["staff_type", "is_active"]
    search_fields = ["employee_code", "person__first_name", "person__last_name"]
    autocomplete_fields = ["person"]
