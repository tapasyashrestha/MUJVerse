"""
MUJVERSE — Reviews Views
Phase 4 Implementation: Post-event attendee feedback, one-per-student enforcement,
review validation, organizer review inspection, and notification triggers.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Avg, Count

from mujverse.apps.events.models import Event, EventStatus
from mujverse.apps.registrations.models import Registration, RegistrationStatus
from mujverse.apps.notifications.models import NotificationType
from mujverse.apps.notifications.services import notify
from .models import Review
from .forms import ReviewForm


def can_user_review_event(user, event):
    """
    Validation logic for student review eligibility:
    1. Must be authenticated and student (or non-organizer attendee).
    2. Event must have concluded (end_datetime < now).
    3. User must have a confirmed registration for the event.
    4. User must not have already submitted a review for this event.
    """
    if not user.is_authenticated:
        return False, "You must be logged in to review an event."

    now = timezone.now()
    if now <= event.end_datetime:
        return False, "You can only review an event after it has concluded."

    has_confirmed_reg = Registration.objects.filter(
        event=event,
        student=user,
        status=RegistrationStatus.CONFIRMED,
    ).exists()

    if not has_confirmed_reg:
        return False, "Only registered attendees can submit a review for this event."

    already_reviewed = Review.objects.filter(event=event, student=user).exists()
    if already_reviewed:
        return False, "You have already reviewed this event."

    return True, ""


@login_required
def create_review_view(request, event_id):
    """
    Allows eligible students to submit an event review once the event has concluded.
    """
    event = get_object_or_404(Event, id=event_id)

    eligible, reason = can_user_review_event(request.user, event)
    if not eligible:
        messages.error(request, reason)
        return redirect(event.get_absolute_url())

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.event = event
            review.student = request.user
            review.save()

            # Notify the organizer
            notify(
                recipient=event.organizer,
                title="New Event Review",
                message=f"{request.user.profile.display_name or request.user.username} gave '{event.title}' {review.rating}★ rating: \"{review.comment[:60]}...\"",
                notification_type=NotificationType.INFO,
                target_url=reverse("reviews:organizer_reviews", kwargs={"pk": event.id}),
            )

            messages.success(request, f"Thank you! Your {review.rating}-star review for '{event.title}' has been submitted.")
            return redirect(event.get_absolute_url())
    else:
        form = ReviewForm()

    return render(request, "reviews/review_form.html", {
        "event": event,
        "form": form,
    })


@login_required
def student_reviews_view(request):
    """List reviews submitted by the authenticated student."""
    reviews = (
        Review.objects.filter(student=request.user)
        .select_related("event", "event__category")
        .order_by("-created_at")
    )
    return render(request, "student/reviews.html", {"reviews": reviews})


@login_required
def organizer_event_reviews_view(request, pk):
    """
    View reviews submitted for an organizer's own event.
    Only authorized organizers and administrators can view.
    """
    event = get_object_or_404(Event, pk=pk)

    is_owner = event.organizer_id == request.user.id
    is_admin = request.user.is_staff or (getattr(request.user, "profile", None) and request.user.profile.is_admin)

    if not (is_owner or is_admin):
        raise PermissionDenied("You can only inspect reviews for your own events.")

    reviews = (
        Review.objects.filter(event=event)
        .select_related("student", "student__profile")
        .order_by("-created_at")
    )

    avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"] or 0.0
    rating_counts = {
        i: reviews.filter(rating=i).count() for i in range(1, 6)
    }

    context = {
        "event": event,
        "reviews": reviews,
        "total_reviews": reviews.count(),
        "avg_rating": round(avg_rating, 1),
        "rating_counts": rating_counts,
    }
    return render(request, "organizer/event_reviews.html", context)
