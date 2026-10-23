"""
MUJVERSE — In-App Notifications Models
"""

from django.db import models
from django.contrib.auth.models import User


class NotificationType(models.TextChoices):
    INFO = "info", "Information"
    APPROVAL = "approval", "Event Approved"
    REJECTION = "rejection", "Event Rejected"
    REGISTRATION = "registration", "Registration Confirmed"
    CANCELLATION = "cancellation", "Registration Cancelled"
    EVENT_UPDATE = "event_update", "Event Update"
    REMINDER = "reminder", "Event Reminder"


class Notification(models.Model):
    """
    Targeted in-app notification delivered to a specific user.
    """
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    title = models.CharField(max_length=150)
    message = models.TextField(max_length=500)
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )
    target_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional local application URL to redirect on click.",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
        ]

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
