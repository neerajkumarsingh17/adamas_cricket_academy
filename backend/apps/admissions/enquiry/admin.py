from django.contrib import admin

from .models import Enquiry, EnquiryFollowUp


class EnquiryFollowUpInline(admin.TabularInline):
    model = EnquiryFollowUp
    extra = 0


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ["enquiry_no", "student_name", "status", "source", "owner", "created_at"]
    list_filter = ["status", "source", "playing_role"]
    search_fields = ["enquiry_no", "student_name", "guardian_name", "guardian_mobile"]
    autocomplete_fields = ["person", "source", "owner"]
    inlines = [EnquiryFollowUpInline]


@admin.register(EnquiryFollowUp)
class EnquiryFollowUpAdmin(admin.ModelAdmin):
    list_display = ["enquiry", "contacted_on", "mode", "next_action_on", "created_by"]
    list_filter = ["mode"]
    search_fields = ["enquiry__enquiry_no", "enquiry__student_name"]
    autocomplete_fields = ["enquiry", "created_by"]
