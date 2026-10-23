"""
MUJVERSE — Registrations & QR Tickets Models
Enforces transactional capacity limits and cryptographic ticket tokens.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from mujverse.apps.events.models import Event


class RegistrationStatus(models.TextChoices):
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"


def generate_ticket_token():
    return uuid.uuid4().hex


class Registration(models.Model):
    """
    Confirmed or cancelled free event registration for an MUJ student.
    Contains a unique, unpredictable ticket_token used for secure QR generation.
    """
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations",
        db_index=True,
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="registrations",
        db_index=True,
    )
    ticket_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_ticket_token,
        db_index=True,
        editable=False,
        help_text="Opaque, unpredictable UUID token for QR ticketing and verification.",
    )
    status = models.CharField(
        max_length=20,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.CONFIRMED,
        db_index=True,
    )
    registered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Event Registration"
        verbose_name_plural = "Event Registrations"
        ordering = ["-registered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "student"],
                name="unique_student_event_registration",
            )
        ]
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.event.title} [{self.get_status_display()}]"

    @property
    def is_confirmed(self) -> bool:
        return self.status == RegistrationStatus.CONFIRMED

    @property
    def is_checked_in(self) -> bool:
        return hasattr(self, "attendance")

    def cancel(self):
        """
        Cancels the registration if allowed (cannot cancel if checked in).
        """
        if self.is_checked_in:
            raise ValueError("Cannot cancel a registration that has already been checked in.")
        self.status = RegistrationStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.save(update_fields=["status", "cancelled_at"])
