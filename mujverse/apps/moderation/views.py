"""
MUJVERSE — Platform Moderation & Administration Views
Restricted exclusively to Administrators.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from mujverse.apps.accounts.decorators import admin_required
from mujverse.apps.events.models import Event, EventStatus, Category
from mujverse.apps.registrations.models import Registration
from mujverse.apps.attendance.models import Attendance
from .models import EventReport, AuditLog


@admin_required
def admin_dashboard_view(request):
    """
    Platform administrator dashboard with real system metrics and pending actions.
    """
    total_users = User.objects.count()
    student_users = User.objects.filter(profile__role="student").count()
    organizer_users = User.objects.filter(profile__role="organizer").count()

    pending_events = Event.objects.filter(status=EventStatus.PENDING_APPROVAL).select_related("organizer", "category")
    approved_events_count = Event.objects.filter(status=EventStatus.APPROVED).count()

    total_registrations = Registration.objects.filter(status="confirmed").count()
    total_attendance = Attendance.objects.count()

    open_reports_count = EventReport.objects.filter(status="open").count()
    recent_audit_logs = AuditLog.objects.select_related("actor")[:10]

    context = {
        "total_users": total_users,
        "student_users": student_users,
        "organizer_users": organizer_users,
        "pending_events": pending_events[:5],
        "pending_events_count": pending_events.count(),
        "approved_events_count": approved_events_count,
        "total_registrations": total_registrations,
        "total_attendance": total_attendance,
        "open_reports_count": open_reports_count,
        "recent_audit_logs": recent_audit_logs,
    }
    return render(request, "admin_dashboard/dashboard.html", context)


@admin_required
def pending_events_view(request):
    """List all events awaiting administrative review and approval."""
    events = Event.objects.filter(status=EventStatus.PENDING_APPROVAL).select_related("organizer", "category").order_by("-created_at")
    return render(request, "admin_dashboard/pending_events.html", {"events": events})


@admin_required
def users_list_view(request):
    """User management view for administrators."""
    users = User.objects.select_related("profile").order_by("-date_joined")[:50]
    return render(request, "admin_dashboard/users.html", {"users_list": users})


@admin_required
def categories_admin_view(request):
    """Category management view."""
    categories = Category.objects.all().order_by("name")
    return render(request, "admin_dashboard/categories.html", {"categories": categories})


@admin_required
def reports_admin_view(request):
    """Content reports moderation queue."""
    reports = EventReport.objects.select_related("reported_by", "event", "reported_user").order_by("-created_at")
    return render(request, "admin_dashboard/reports.html", {"reports": reports})
