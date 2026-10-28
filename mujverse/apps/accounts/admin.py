"""
MUJVERSE — Accounts Admin
Provides clear user, profile, club, and membership management in Django Admin.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, RoleChoices, AccountStatus, Club, ClubMembership, ApprovalStatus


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "MUJVERSE Profile"
    fk_name = "user"
    fields = (
        "role",
        "status",
        "display_name",
        "student_identifier",
        "branch",
        "course",
        "academic_year",
        "semester",
        "profile_image",
        "bio",
    )


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "get_role",
        "get_status",
        "get_student_id",
        "is_staff",
    )
    list_filter = ("profile__role", "profile__status", "is_staff", "is_superuser", "is_active")

    @admin.display(description="Role", ordering="profile__role")
    def get_role(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_role_display() if profile else "No Profile"

    @admin.display(description="Status", ordering="profile__status")
    def get_status(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_status_display() if profile else "-"

    @admin.display(description="Student ID", ordering="profile__student_identifier")
    def get_student_id(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.student_identifier if profile else "-"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "status",
        "display_name",
        "student_identifier",
        "branch",
        "course",
        "academic_year",
        "created_at",
    )
    list_filter = ("role", "status", "branch", "course", "academic_year", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "display_name",
        "student_identifier",
        "branch",
    )
    readonly_fields = ("created_at", "updated_at")
    actions = ["approve_organizer_accounts", "promote_to_organizer", "demote_to_student"]

    @admin.action(description="Approve selected Organizer account(s)")
    def approve_organizer_accounts(self, request, queryset):
        count = queryset.filter(role=RoleChoices.ORGANIZER).update(status=AccountStatus.ACTIVE)
        # Also approve their pending club memberships
        for prof in queryset.filter(role=RoleChoices.ORGANIZER):
            ClubMembership.objects.filter(user=prof.user, approval_status=ApprovalStatus.PENDING).update(
                approval_status=ApprovalStatus.APPROVED,
                reviewed_by=request.user,
            )
        self.message_user(request, f"Approved {count} organizer account(s).")

    @admin.action(description="Promote selected users to Organizer role")
    def promote_to_organizer(self, request, queryset):
        count = queryset.update(role=RoleChoices.ORGANIZER, status=AccountStatus.ACTIVE)
        self.message_user(request, f"Successfully promoted {count} user(s) to Organizer.")

    @admin.action(description="Demote selected users to Student role")
    def demote_to_student(self, request, queryset):
        count = queryset.update(role=RoleChoices.STUDENT, status=AccountStatus.ACTIVE)
        self.message_user(request, f"Successfully demoted {count} user(s) to Student.")


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "verification_status", "created_at", "members_count")
    list_filter = ("verification_status", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    actions = ["approve_clubs", "reject_clubs"]

    def members_count(self, obj):
        return obj.memberships.count()
    members_count.short_description = "Members"

    @admin.action(description="Approve selected clubs")
    def approve_clubs(self, request, queryset):
        count = queryset.update(verification_status=ApprovalStatus.APPROVED)
        self.message_user(request, f"Approved {count} club(s).")

    @admin.action(description="Reject selected clubs")
    def reject_clubs(self, request, queryset):
        count = queryset.update(verification_status=ApprovalStatus.REJECTED)
        self.message_user(request, f"Rejected {count} club(s).")


@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "position", "approval_status", "created_at")
    list_filter = ("approval_status", "position", "club", "created_at")
    search_fields = ("user__username", "user__email", "club__name")
    actions = ["approve_memberships", "reject_memberships"]

    @admin.action(description="Approve selected club memberships")
    def approve_memberships(self, request, queryset):
        for m in queryset:
            m.approval_status = ApprovalStatus.APPROVED
            m.reviewed_by = request.user
            m.save()
            # Also activate profile if user is organizer
            profile = getattr(m.user, "profile", None)
            if profile and profile.role == RoleChoices.ORGANIZER:
                profile.status = AccountStatus.ACTIVE
                profile.save(update_fields=["status"])
        self.message_user(request, f"Approved {queryset.count()} membership(s).")

    @admin.action(description="Reject selected club memberships")
    def reject_memberships(self, request, queryset):
        count = queryset.update(approval_status=ApprovalStatus.REJECTED, reviewed_by=request.user)
        self.message_user(request, f"Rejected {count} membership(s).")


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
