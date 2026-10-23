"""
MUJVERSE — Reviews Views
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Review


@login_required
def student_reviews_view(request):
    """List reviews submitted by the student."""
    reviews = Review.objects.filter(student=request.user).select_related("event")
    return render(request, "student/reviews.html", {"reviews": reviews})
