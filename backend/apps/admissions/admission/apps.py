from django.apps import AppConfig


class AdmissionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admissions.admission"
    label = "admission"
    verbose_name = "Admission Management"
