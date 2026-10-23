"""
MUJVERSE — Events Models
Category and Event entities enforcing strict lifecycle state machine and business validation.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.urls import reverse


class Category(models.Model):
    """
    Event category (e.g., Cultural, Technical, Sports, Workshops, Hackathons).
    """
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True, max_length=300)
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="bi-calendar-event",
        help_text="Bootstrap Icons class name (e.g. bi-code-slash, bi-music-note).",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Event Category"
        verbose_name_plural = "Event Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class EventStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class EventQuerySet(models.QuerySet):
    def publicly_visible(self):
        """
        Public events must be approved, marked as published, and not cancelled or draft.
        """
        return self.filter(
            status__in=[EventStatus.APPROVED, EventStatus.COMPLETED],
            is_published=True,
        )

    def upcoming(self):
        return self.publicly_visible().filter(start_datetime__gte=timezone.now()).order_by("start_datetime")

    def featured(self):
        return self.publicly_visible().filter(start_datetime__gte=timezone.now()).order_by("start_datetime")[:6]


class Event(models.Model):
    """
    Primary Campus Event model.
    Follows state machine: draft -> pending_approval -> approved/rejected -> completed
    """
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(help_text="Full markdown or text event description.")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="events",
    )
    organizer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="organized_events",
        help_text="The authorized organizer account managing this event.",
    )
    cover_image = models.ImageField(
        upload_to="events/covers/%Y/%m/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
        help_text="Banner/poster image for event cards and details.",
    )
    venue = models.CharField(max_length=150, help_text="Campus venue, hall, or room.")
    start_datetime = models.DateTimeField(db_index=True, help_text="When the event starts.")
    end_datetime = models.DateTimeField(help_text="When the event concludes.")
    registration_deadline = models.DateTimeField(
        db_index=True,
        help_text="Cut-off date & time for new registrations.",
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Maximum total allowed attendees (must be at least 1).",
    )
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT,
        db_index=True,
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text="Administrator note explaining why the event was rejected.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Controls public visibility once approved by platform admin.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        verbose_name = "Campus Event"
        verbose_name_plural = "Campus Events"
        ordering = ["-start_datetime"]
        indexes = [
            models.Index(fields=["status", "is_published", "start_datetime"]),
            models.Index(fields=["organizer", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        errors = {}
        if self.start_datetime and self.end_datetime:
            if self.end_datetime <= self.start_datetime:
                errors["end_datetime"] = "Event end time must be after the start time."
        if self.registration_deadline and self.start_datetime:
            if self.registration_deadline > self.start_datetime:
                errors["registration_deadline"] = "Registration deadline cannot be after the event has started."
        if self.capacity is not None and self.capacity < 1:
            errors["capacity"] = "Capacity must be a positive integer greater than zero."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "event"
            candidate = base_slug
            idx = 1
            while Event.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{idx}"
                idx += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("public:event_detail", kwargs={"slug": self.slug})

    @property
    def is_publicly_viewable(self) -> bool:
        return self.status in [EventStatus.APPROVED, EventStatus.COMPLETED] and self.is_published

    @property
    def confirmed_registrations_count(self) -> int:
        return self.registrations.filter(status="confirmed").count()

    @property
    def remaining_seats(self) -> int:
        return max(0, self.capacity - self.confirmed_registrations_count)

    @property
    def is_full(self) -> bool:
        return self.remaining_seats <= 0

    @property
    def is_registration_open(self) -> bool:
        now = timezone.now()
        if not self.is_publicly_viewable:
            return False
        if self.status != EventStatus.APPROVED:
            return False
        if now > self.registration_deadline or now >= self.end_datetime:
            return False
        if self.is_full:
            return False
        return True

    @property
    def attendance_count(self) -> int:
        return self.registrations.filter(attendance__isnull=False).count()

    @property
    def attendance_rate(self) -> float:
        total = self.confirmed_registrations_count
        if total == 0:
            return 0.0
        return round((self.attendance_count / total) * 100, 1)
