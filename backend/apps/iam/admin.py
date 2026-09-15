from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from .models import Permission, Role, RolePermission, User, UserRole


class UserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("login_id", "person")


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 0
    autocomplete_fields = ["role"]


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    list_display = ["login_id", "person", "is_active", "is_staff", "mfa_enabled", "last_login_at"]
    list_filter = ["is_active", "is_staff", "mfa_enabled"]
    search_fields = ["login_id", "person__first_name", "person__last_name"]
    ordering = ["login_id"]
    autocomplete_fields = ["person"]
    readonly_fields = ["last_login_at", "created_at", "updated_at"]
    inlines = [UserRoleInline]

    fieldsets = (
        (None, {"fields": ("login_id", "password")}),
        ("Profile", {"fields": ("person",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "mfa_enabled", "groups")},
        ),
        ("Important dates", {"fields": ("last_login_at", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("login_id", "person", "password1", "password2"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_system"]
    list_filter = ["is_system"]
    search_fields = ["code", "name"]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["module", "verb"]
    list_filter = ["module", "verb"]
    search_fields = ["module"]


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ["role", "permission", "scope"]
    list_filter = ["scope", "role"]
    search_fields = ["role__code", "role__name", "permission__module", "permission__verb"]
    autocomplete_fields = ["role", "permission"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "valid_from", "valid_to"]
    list_filter = ["role"]
    search_fields = ["user__login_id", "role__code"]
    autocomplete_fields = ["user", "role"]
