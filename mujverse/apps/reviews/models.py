"""
MUJVERSE — Reviews Models
Stores post-event ratings and feedback from verified attendees.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from mujverse.apps.events.models import Event


class Review(models.Model):
    """
    Event feedback from a student attendee.
    Enforces one review per student per event.
    """
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="reviews",
        db_index=True,
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews",
        db_index=True,
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars.",
    )
    comment = models.TextField(
        max_length=1000,
        help_text="Attendee review and feedback.",
    )
    is_visible = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Visible to public/organizer. Can be hidden by admin if reported.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Event Review"
        verbose_name_plural = "Event Reviews"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "student"],
                name="unique_event_student_review",
            )
        ]

    def __str__(self):
        return f"{self.student.username} on {self.event.title} ({self.rating}★)"
