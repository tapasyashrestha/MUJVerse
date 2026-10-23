"""
MUJVERSE — Reviews Forms
"""

from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[
            (5, "★★★★★ (5/5) — Excellent"),
            (4, "★★★★☆ (4/5) — Very Good"),
            (3, "★★★☆☆ (3/5) — Good"),
            (2, "★★☆☆☆ (2/5) — Fair"),
            (1, "★☆☆☆☆ (1/5) — Poor"),
        ],
        widget=forms.Select(attrs={"class": "form-select bg-dark text-white border-secondary"}),
        label="Rating",
        help_text="Select your overall rating for this event.",
    )
    comment = forms.CharField(
        min_length=10,
        max_length=1000,
        widget=forms.Textarea(attrs={
            "class": "form-control bg-dark text-white border-secondary",
            "rows": 4,
            "placeholder": "Share your experience, key takeaways, and constructive feedback (10 to 1,000 characters)...",
        }),
        label="Feedback & Review",
        help_text="Minimum 10 characters.",
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
