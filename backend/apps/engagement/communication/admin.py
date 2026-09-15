from django.contrib import admin

from .models import NotificationLog, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "channel", "is_active")
    list_filter = ("channel", "is_active")
    search_fields = ("code", "subject")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("recipient", "channel", "status", "created_at", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("recipient", "provider_message_id")
    readonly_fields = [f.name for f in NotificationLog._meta.fields]

    def has_add_permission(self, request):
        return False
