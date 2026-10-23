"""
MUJVERSE — Moderation & Security Audit Log Models
Ensures all administrative and sensitive operations are logged immutably.
"""

from django.db import models
from django.contrib.auth.models import User
from mujverse.apps.events.models import Event


class ReportStatus(models.TextChoices):
    OPEN = "open", "Open"
    UNDER_REVIEW = "under_review", "Under Review"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class EventReport(models.Model):
    """
    User-submitted reports for inappropriate events, content, or accounts.
    """
    reported_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="submitted_reports",
        db_index=True,
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
    )
    reported_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports_against",
    )
    reason = models.CharField(max_length=150)
    description = models.TextField(max_length=1000)
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_reports",
    )
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Content Report"
        verbose_name_plural = "Content Reports"
        ordering = ["-created_at"]

    def __str__(self):
        target = f"Event: {self.event.title}" if self.event else f"User: {self.reported_user.username}"
        return f"Report #{self.id} on {target} [{self.get_status_display()}]"


class AuditLog(models.Model):
    """
    Immutable audit trail for privileged administrative operations.
    Protected against alteration by ordinary users.
    """
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
        help_text="The administrator or system account that performed the action.",
    )
    action = models.CharField(
        max_length=80,
        db_index=True,
        help_text="e.g. event_approved, event_rejected, user_suspended, category_created",
    )
    object_type = models.CharField(max_length=60, db_index=True)
    object_id = models.CharField(max_length=64)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured action context (passwords and secrets must NEVER be stored here).",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor_name}: {self.action} on {self.object_type}#{self.object_id}"

    @classmethod
    def log(cls, actor, action: str, object_type: str, object_id: str, metadata: dict = None):
        """Helper to create audit records safely."""
        return cls.objects.create(
            actor=actor if (actor and actor.is_authenticated) else None,
            action=action,
            object_type=object_type,
            object_id=str(object_id),
            metadata=metadata or {},
        )
