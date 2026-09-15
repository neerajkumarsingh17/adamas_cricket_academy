from django.db import models

from apps.core.models import AuditedModel
from apps.people.models import Guardian


class PreferredLanguage(models.TextChoices):
    ENGLISH = "en", "English"
    BENGALI = "bn", "Bengali"
    HINDI = "hi", "Hindi"


class ParentPortalAccess(AuditedModel):
    """M05 Parent Management (docs/00-project-structure.md): the parent's
    *portal access*, contact preferences and notification settings — the
    relationship, not the person. `Guardian` (people/) already carries a
    coarse `portal_access` eligibility flag set by staff; this model is the
    parent-facing settings record that flag unlocks.

    Not specified field-by-field in docs/01-data-model.md — only named as
    "portal flag + contact preferences" in docs/00-project-structure.md and
    the build prompt. Fields below are a direct, minimal reading of that
    description.
    """

    guardian = models.OneToOneField(
        Guardian, on_delete=models.CASCADE, related_name="portal_settings"
    )
    is_portal_enabled = models.BooleanField(default=False)
    preferred_language = models.CharField(
        max_length=2, choices=PreferredLanguage.choices, default=PreferredLanguage.ENGLISH
    )
    sms_opt_in = models.BooleanField(default=True)
    whatsapp_opt_in = models.BooleanField(default=True)
    email_opt_in = models.BooleanField(default=True)
    push_opt_in = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Portal settings for {self.guardian}"
