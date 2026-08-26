from django.apps import AppConfig


class EnquiryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admissions.enquiry"
    label = "enquiry"
    verbose_name = "Enquiry Management"
