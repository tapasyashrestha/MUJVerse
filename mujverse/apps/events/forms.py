"""
MUJVERSE — Events Forms
Organizer event creation and editing. Enforces ownership and validates all inputs
including image content type and size on the server side.
"""

import os
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event, Category, EventStatus


class EventForm(forms.ModelForm):
    """
    Unified create/edit form for organizer events.
    Used for draft saving AND submission to moderation.
    """

    class Meta:
        model = Event
        fields = [
            "title",
            "category",
            "cover_image",
            "description",
            "venue",
            "start_datetime",
            "end_datetime",
            "registration_deadline",
            "capacity",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. MUJ Hackathon 2026",
                "maxlength": 200,
            }),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "Describe your event: who it's for, what will happen, how to prepare...",
            }),
            "venue": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Grand Hall 1, Auditorium, Ground B",
            }),
            "start_datetime": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
            "end_datetime": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
            "registration_deadline": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
            "capacity": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "max": 10000,
            }),
            "cover_image": forms.FileInput(attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["category"].empty_label = "— Select a Category —"
        self.fields["cover_image"].required = False

        # Set input_formats for datetime fields
        for f in ("start_datetime", "end_datetime", "registration_deadline"):
            self.fields[f].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"]

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 5:
            raise ValidationError("Event title must be at least 5 characters long.")
        return title

    def clean_description(self):
        desc = self.cleaned_data.get("description", "").strip()
        if len(desc) < 30:
            raise ValidationError("Please provide a more detailed description (at least 30 characters).")
        return desc

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")
        if capacity is not None and capacity < 1:
            raise ValidationError("Capacity must be at least 1.")
        return capacity

    def clean_cover_image(self):
        """
        Server-side image validation: file extension, MIME content type, and size.
        Does NOT rely on client-side accept attribute alone.
        """
        image = self.cleaned_data.get("cover_image")
        if not image:
            return image

        # Check file size (max 5MB)
        max_mb = 5
        if hasattr(image, "size") and image.size > max_mb * 1024 * 1024:
            raise ValidationError(f"Image file is too large. Maximum allowed size is {max_mb}MB.")

        # Check extension
        allowed_exts = [".jpg", ".jpeg", ".png", ".webp"]
        ext = os.path.splitext(image.name)[1].lower()
        if ext not in allowed_exts:
            raise ValidationError("Invalid image format. Allowed formats: JPG, PNG, WebP.")

        # Check content type header
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if hasattr(image, "content_type") and image.content_type not in allowed_types:
            raise ValidationError("Invalid image content type. Upload a JPEG, PNG, or WebP image.")

        return image

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_datetime")
        end = cleaned_data.get("end_datetime")
        deadline = cleaned_data.get("registration_deadline")

        if start and end:
            if end <= start:
                self.add_error("end_datetime", "Event end time must be after the start time.")

        if start and deadline:
            if deadline > start:
                self.add_error(
                    "registration_deadline",
                    "Registration deadline cannot be after the event has started.",
                )

        if start and start <= timezone.now():
            self.add_error("start_datetime", "Event start time must be in the future.")

        return cleaned_data


class EventRejectForm(forms.Form):
    """Simple form requiring a rejection reason from the administrator."""
    rejection_reason = forms.CharField(
        min_length=10,
        max_length=1000,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Please explain why this event was rejected and what changes are needed for resubmission...",
        }),
        label="Rejection Reason",
        help_text="The organizer will see this message and can correct their submission accordingly.",
    )
