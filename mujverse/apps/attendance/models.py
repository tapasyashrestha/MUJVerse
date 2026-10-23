"""
MUJVERSE — Attendance Models
One-to-One relationship with Registration guarantees single-use check-in.
"""

from django.db import models
from django.contrib.auth.models import User
from mujverse.apps.registrations.models import Registration


class CheckInMethod(models.TextChoices):
    QR_SCAN = "qr_scan", "QR Code Scan"
    MANUAL = "manual", "Manual Token Entry"


class Attendance(models.Model):
    """
    Atomic record of student attendance verification.
    """
    registration = models.OneToOneField(
        Registration,
        on_delete=models.CASCADE,
        related_name="attendance",
        help_text="One-to-one link strictly prevents duplicate check-in.",
    )
    checked_in_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="verified_attendances",
        help_text="The authorized organizer or admin who scanned the ticket.",
    )
    checked_in_at = models.DateTimeField(auto_now_add=True, db_index=True)
    method = models.CharField(
        max_length=20,
        choices=CheckInMethod.choices,
        default=CheckInMethod.QR_SCAN,
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        ordering = ["-checked_in_at"]

    def __str__(self):
        return f"Attended: {self.registration.student.username} at {self.registration.event.title}"
