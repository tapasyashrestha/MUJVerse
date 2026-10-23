"""
MUJVERSE — Student Registrations & Dashboard Views
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from mujverse.apps.accounts.decorators import student_required
from .models import Registration


@login_required
def student_dashboard_view(request):
    """
    Student dashboard displaying real upcoming registrations, past events, and ticket access.
    """
    user = request.user
    now = timezone.now()

    my_registrations = Registration.objects.filter(
        student=user,
        status="confirmed",
    ).select_related("event", "event__category").order_by("event__start_datetime")

    upcoming = my_registrations.filter(event__end_datetime__gte=now)
    past = my_registrations.filter(event__end_datetime__lt=now)

    context = {
        "upcoming_registrations": upcoming,
        "past_registrations": past,
        "total_registered": my_registrations.count(),
        "total_attended": Registration.objects.filter(student=user, attendance__isnull=False).count(),
    }
    return render(request, "student/dashboard.html", context)


@login_required
def student_registrations_list_view(request):
    """List all registrations for the authenticated student."""
    registrations = Registration.objects.filter(student=request.user).select_related("event", "event__category").order_by("-registered_at")
    return render(request, "student/registrations.html", {"registrations": registrations})


@login_required
def ticket_detail_view(request, ticket_token):
    """
    Displays the unique QR ticket for the authenticated student.
    Guarantees user cannot view another student's ticket.
    """
    registration = get_object_or_404(
        Registration.objects.select_related("event", "student", "student__profile"),
        ticket_token=ticket_token,
    )

    # Server-side authorization check: only owner, event organizer, or admin can view ticket
    user = request.user
    is_owner = registration.student_id == user.id
    is_organizer = registration.event.organizer_id == user.id
    is_admin_user = user.is_staff or (getattr(user, "profile", None) and user.profile.is_admin)

    if not (is_owner or is_organizer or is_admin_user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You do not have permission to view this ticket.")

    return render(request, "student/ticket_detail.html", {"registration": registration})
