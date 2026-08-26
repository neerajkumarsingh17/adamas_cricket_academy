from django.apps import AppConfig


class IdcardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admissions.idcard"
    label = "idcard"
    verbose_name = "ID Card Management"
