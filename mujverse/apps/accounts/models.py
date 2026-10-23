"""
MUJVERSE — Accounts Models
Defines user profiles and role-based permissions.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class RoleChoices(models.TextChoices):
    STUDENT = "student", "Student"
    ORGANIZER = "organizer", "Organizer"
    ADMIN = "admin", "Administrator"


class Profile(models.Model):
    """
    Extends standard Django User with MUJVERSE role and campus profile attributes.
    Server-side checks strictly verify this role; client input cannot modify role.
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
    display_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Name displayed publicly and on event tickets.",
    )
    student_identifier = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        verbose_name="Registration / Student ID",
        help_text="MUJ Registration number (e.g., 229301234). Access-restricted.",
    )
    department = models.CharField(
        max_length=120,
        blank=True,
        help_text="Academic Department (e.g., Computer Science & Engineering).",
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
        return self.role == RoleChoices.ORGANIZER

    @property
    def is_admin(self) -> bool:
        return self.role == RoleChoices.ADMIN or self.user.is_staff or self.user.is_superuser
