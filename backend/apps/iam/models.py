from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import AuditedModel, TimeStampedModel
from apps.people.models import Person


class UserManager(BaseUserManager["User"]):
    def create_user(self, login_id: str, password: str | None = None, **extra_fields):
        if not login_id:
            raise ValueError("login_id is required")
        user = self.model(login_id=login_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login_id: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(login_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """docs/01-data-model.md section 1."""

    login_id = models.CharField(max_length=255, unique=True)
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_accounts",
        help_text="Null only for the system/IT admin account.",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)
    mfa_enabled = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "login_id"
    REQUIRED_FIELDS = []

    def has_perm_for(self, module: str, verb: str) -> bool:
        """docs/03-rbac.md — the only permission check in the codebase.
        Resolved from UserRole -> RolePermission -> Permission, cached on
        this instance (i.e. for the life of one request's request.user).
        """
        return (module, verb) in self.resolved_permissions()

    def scope_for(self, module: str, verb: str) -> str | None:
        """The widest scope ("all" beats "own") this user holds for
        module+verb across all their currently-valid roles, or None if the
        permission isn't granted at all.
        """
        return self.resolved_permissions().get((module, verb))

    def current_roles(self) -> models.QuerySet["Role"]:
        """Roles held right now — valid_from has passed and valid_to
        hasn't, or is null.
        """
        return Role.objects.filter(pk__in=self._current_role_ids())

    def resolved_permissions(self) -> dict[tuple[str, str], str]:
        """{(module, verb): widest_scope} across the user's currently-valid
        roles. "all" always wins over "own" regardless of which role is
        seen first (docs/03-rbac.md: "the widest scope among them"). Used
        by has_perm_for/scope_for and echoed flat in GET /auth/me.
        """
        if not hasattr(self, "_permission_cache"):
            grants = RolePermission.objects.filter(
                role_id__in=self._current_role_ids()
            ).values_list("permission__module", "permission__verb", "scope")
            cache: dict[tuple[str, str], str] = {}
            for module, verb, scope in grants:
                key = (module, verb)
                if key not in cache or scope == Scope.ALL:
                    cache[key] = scope
            self._permission_cache = cache
        return self._permission_cache

    def _current_role_ids(self):
        # localdate(), not now().date(): valid_from/valid_to are calendar
        # days in the academy's own timezone (CLAUDE.md: "Timezone is
        # Asia/Kolkata"), not UTC — now().date() is the UTC date, which
        # lags IST by up to a day during the ~5.5h window after IST
        # midnight but before UTC midnight. A role granted "from today"
        # (apps.iam.services.get_or_create_user_for_person) during that
        # window would otherwise not be considered current until the
        # following UTC day.
        today = timezone.localdate()
        return (
            self.user_roles.filter(valid_from__lte=today)
            .filter(models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=today))
            .values_list("role_id", flat=True)
        )

    def __str__(self) -> str:
        return self.login_id


class Role(AuditedModel):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Verb(models.TextChoices):
    VIEW = "view", "View"
    ADD = "add", "Add"
    EDIT = "edit", "Edit"
    APPROVE = "approve", "Approve"
    EXPORT = "export", "Export"
    PRINT = "print", "Print"


class Permission(AuditedModel):
    module = models.SlugField(max_length=50)
    verb = models.CharField(max_length=10, choices=Verb.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["module", "verb"], name="unique_permission_module_verb"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.module}:{self.verb}"


class Scope(models.TextChoices):
    ALL = "all", "All"
    OWN = "own", "Own"


class RolePermission(AuditedModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions"
    )
    scope = models.CharField(max_length=3, choices=Scope.choices, default=Scope.ALL)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="unique_role_permission"),
        ]

    def __str__(self) -> str:
        return f"{self.role.code} -> {self.permission} ({self.scope})"


class UserRole(AuditedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user} as {self.role.code}"
