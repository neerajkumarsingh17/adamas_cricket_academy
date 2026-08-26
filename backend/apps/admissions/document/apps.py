from django.apps import AppConfig


class DocumentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admissions.document"
    label = "document"
    verbose_name = "Document Management"
