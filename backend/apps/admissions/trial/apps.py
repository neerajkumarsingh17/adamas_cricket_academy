from django.apps import AppConfig


class TrialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admissions.trial"
    label = "trial"
    verbose_name = "Trial Management"
