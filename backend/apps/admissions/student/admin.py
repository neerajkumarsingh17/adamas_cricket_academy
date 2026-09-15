from django.contrib import admin

from .models import Student, StudentStatusHistory


class StudentStatusHistoryInline(admin.TabularInline):
    model = StudentStatusHistory
    extra = 0
    autocomplete_fields = ["changed_by"]
    readonly_fields = ["changed_at"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["student_code", "person", "programme", "status", "admission_date"]
    list_filter = ["status", "programme", "residential"]
    search_fields = ["student_code", "person__first_name", "person__last_name"]
    autocomplete_fields = ["person", "admission", "programme"]
    inlines = [StudentStatusHistoryInline]


@admin.register(StudentStatusHistory)
class StudentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["student", "from_status", "to_status", "changed_by", "changed_at"]
    list_filter = ["to_status"]
    search_fields = ["student__student_code"]
    autocomplete_fields = ["student", "changed_by"]
