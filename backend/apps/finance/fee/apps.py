from django.apps import AppConfig


class FeeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance.fee"
    label = "fee"
    verbose_name = "Fee"
