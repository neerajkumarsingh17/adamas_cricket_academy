from django.apps import AppConfig


class StudentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admissions.student"
    label = "student"
    verbose_name = "Student Management"
