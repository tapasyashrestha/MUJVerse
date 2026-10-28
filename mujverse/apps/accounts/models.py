"""
MUJVERSE — Accounts Models
Defines user profiles, roles, clubs, and club memberships with administrative verification.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify


class RoleChoices(models.TextChoices):
    STUDENT = "student", "Student"
    ORGANIZER = "organizer", "Organizer"
    ADMIN = "admin", "Administrator"


class AccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PENDING = "pending", "Pending Approval"
    SUSPENDED = "suspended", "Suspended"


class ClubPosition(models.TextChoices):
    PRESIDENT = "president", "President"
    VICE_PRESIDENT = "vice_president", "Vice President"
    CORE_COMMITTEE = "core_committee", "Core Committee Member"
    OTHER = "other", "Other Authorized Position"


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Club(models.Model):
    """
    Campus Club / Student Chapter entity representing student organizations.
    """
    name = models.CharField(max_length=150, unique=True, db_index=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Club vision, mission, and activities.")
    verification_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Club"
        verbose_name_plural = "Clubs"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Profile(models.Model):
    """
    Extends standard Django User with MUJVERSE role, campus credentials, and academic details.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="User Account",
    )
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.STUDENT,
        db_index=True,
        help_text="User role determining platform permissions. Cannot be changed by the user.",
    )
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
        help_text="Account moderation status.",
    )
    display_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Name displayed publicly and on event tickets.",
    )
    student_identifier = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Registration / Student ID",
        help_text="Unique MUJ Registration number (e.g., 229301234).",
    )
    branch = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Branch / Department",
        help_text="e.g. Computer Science & Engineering, Information Technology",
    )
    department = models.CharField(
        max_length=120,
        blank=True,
        help_text="Legacy department field for backwards compatibility.",
    )
    course = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Course / Degree",
        help_text="e.g. B.Tech, BCA, M.Tech, MBA",
    )
    academic_year = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Current Academic Year",
        help_text="e.g. 1st Year, 2nd Year, 3rd Year, 4th Year",
    )
    semester = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Current Semester",
        help_text="e.g. 1, 2, 3, 4, 5, 6, 7, 8",
    )
    profile_image = models.ImageField(
        upload_to="profiles/%Y/%m/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
        help_text="Upload a square JPEG/PNG/WebP image (max 5MB).",
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="Brief student or organizer bio (max 500 characters).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["-created_at"]

    def __str__(self):
        name = self.display_name or self.user.get_full_name() or self.user.username
        return f"{name} ({self.get_role_display()})"

    @property
    def is_student(self) -> bool:
        return self.role == RoleChoices.STUDENT

    @property
    def is_organizer(self) -> bool:
        """
        An organizer must have the organizer role AND approved account status.
        """
        if self.role != RoleChoices.ORGANIZER:
            return False
        return self.status == AccountStatus.ACTIVE

    @property
    def is_pending_organizer(self) -> bool:
        return self.role == RoleChoices.ORGANIZER and self.status == AccountStatus.PENDING

    @property
    def is_admin(self) -> bool:
        return self.role == RoleChoices.ADMIN or self.user.is_staff or self.user.is_superuser


class ClubMembership(models.Model):
    """
    Connects a User to a Club with position and verification workflow.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="club_memberships",
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    position = models.CharField(
        max_length=50,
        choices=ClubPosition.choices,
        default=ClubPosition.CORE_COMMITTEE,
    )
    position_detail = models.CharField(
        max_length=100,
        blank=True,
        help_text="Custom title if position is 'Other'",
    )
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_memberships",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Club Membership"
        verbose_name_plural = "Club Memberships"
        unique_together = ("user", "club")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} — {self.club.name} ({self.get_position_display()} - {self.get_approval_status_display()})"
