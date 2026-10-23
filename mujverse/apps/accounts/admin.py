"""
MUJVERSE — Accounts Admin
Provides clear user and profile management in Django Admin.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, RoleChoices


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "MUJVERSE Profile"
    fk_name = "user"
    fields = ("role", "display_name", "student_identifier", "department", "profile_image", "bio")


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "get_role",
        "get_student_id",
        "is_staff",
    )
    list_filter = ("profile__role", "is_staff", "is_superuser", "is_active")

    @admin.display(description="Role", ordering="profile__role")
    def get_role(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_role_display() if profile else "No Profile"

    @admin.display(description="Student ID", ordering="profile__student_identifier")
    def get_student_id(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.student_identifier if profile else "-"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "display_name",
        "student_identifier",
        "department",
        "created_at",
    )
    list_filter = ("role", "department", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "display_name",
        "student_identifier",
        "department",
    )
    readonly_fields = ("created_at", "updated_at")
    actions = ["promote_to_organizer", "demote_to_student"]

    @admin.action(description="Promote selected users to Organizer role")
    def promote_to_organizer(self, request, queryset):
        count = queryset.update(role=RoleChoices.ORGANIZER)
        self.message_user(request, f"Successfully promoted {count} user(s) to Organizer.")

    @admin.action(description="Demote selected users to Student role")
    def demote_to_student(self, request, queryset):
        count = queryset.update(role=RoleChoices.STUDENT)
        self.message_user(request, f"Successfully demoted {count} user(s) to Student.")


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
