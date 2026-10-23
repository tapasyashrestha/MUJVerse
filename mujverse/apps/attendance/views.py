"""
MUJVERSE — Attendance Views & Verification Scanner Endpoint
Phase 3 Implementation: Real-time QR scanner terminal, manual token fallback,
atomic check-in verification, duplicate prevention, and ownership authorization.
"""

import json
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
from django.utils import timezone
from mujverse.apps.accounts.decorators import organizer_required
from mujverse.apps.events.models import Event
from mujverse.apps.registrations.models import Registration, RegistrationStatus
from mujverse.apps.notifications.models import NotificationType
from mujverse.apps.notifications.services import notify
from .models import Attendance, CheckInMethod


def _can_manage_event_attendance(user, event):
    """Check if user is the owning organizer or an administrator."""
    if not user.is_authenticated:
        return False
    if user.is_staff or (getattr(user, "profile", None) and user.profile.is_admin):
        return True
    return event.organizer_id == user.id


@login_required
def scanner_view(request, event_id):
    """
    QR code scanner page for an authorized organizer or admin.
    """
    event = get_object_or_404(Event, id=event_id)
    if not _can_manage_event_attendance(request.user, event):
        raise PermissionDenied("You can only access the scanner for your own events.")

    recent_attendances = (
        Attendance.objects.filter(registration__event=event)
        .select_related("registration__student", "registration__student__profile", "checked_in_by")
        .order_by("-checked_in_at")[:10]
    )

    context = {
        "event": event,
        "recent_attendances": recent_attendances,
    }
    return render(request, "organizer/scanner.html", context)


@login_required
@require_POST
def verify_checkin_api(request, event_id):
    """
    Backend check-in verification endpoint.
    Verifies event ownership, token authenticity, event alignment, status, and single-use constraint.
    Atomically writes Attendance record.
    """
    event = get_object_or_404(Event, id=event_id)
    if not _can_manage_event_attendance(request.user, event):
        return JsonResponse({
            "success": False,
            "code": "FORBIDDEN",
            "message": "Unauthorized: You do not have permission to check in attendees for this event.",
        }, status=403)

    # Parse input from JSON or form post
    token = ""
    method_str = "qr_scan"
    notes = ""

    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
            token = data.get("token", "")
            method_str = data.get("method", "qr_scan")
            notes = data.get("notes", "")
        except Exception:
            return JsonResponse({
                "success": False,
                "code": "INVALID_JSON",
                "message": "Malformed JSON payload.",
            }, status=400)
    else:
        token = request.POST.get("token", "")
        method_str = request.POST.get("method", "manual")
        notes = request.POST.get("notes", "")

    token = token.strip()
    # If a full URL was scanned, extract trailing token segment
    if "/" in token:
        parts = [p.strip() for p in token.split("/") if p.strip()]
        if parts:
            token = parts[-1]

    if not token:
        return JsonResponse({
            "success": False,
            "code": "EMPTY_TOKEN",
            "message": "Please scan a QR code or enter a ticket token.",
        }, status=400)

    # 1. Lookup Registration
    registration = (
        Registration.objects.filter(ticket_token=token)
        .select_related("student", "student__profile", "event")
        .first()
    )

    if not registration:
        return JsonResponse({
            "success": False,
            "code": "NOT_FOUND",
            "message": "Invalid ticket token. No matching registration found.",
        }, status=404)

    # 2. Check event alignment (Wrong Event)
    if registration.event_id != event.id:
        return JsonResponse({
            "success": False,
            "code": "WRONG_EVENT",
            "message": f"Wrong event! This ticket is for '{registration.event.title}', not this event.",
            "ticket_event_title": registration.event.title,
        }, status=400)

    # 3. Check registration status (Cancelled)
    if registration.status == RegistrationStatus.CANCELLED:
        cancelled_str = (
            registration.cancelled_at.strftime("%b %d, %I:%M %p")
            if registration.cancelled_at
            else "previously"
        )
        return JsonResponse({
            "success": False,
            "code": "CANCELLED",
            "message": f"Entry denied: This registration was cancelled ({cancelled_str}).",
        }, status=400)

    # 4. Check single-use constraint (Already Checked In)
    if hasattr(registration, "attendance"):
        existing = registration.attendance
        checkin_time = existing.checked_in_at.strftime("%I:%M:%S %p")
        return JsonResponse({
            "success": False,
            "code": "ALREADY_CHECKED_IN",
            "message": f"Duplicate scan: Ticket already verified at {checkin_time}.",
            "attendee": {
                "name": registration.student.profile.display_name or registration.student.username,
                "student_id": registration.student.profile.student_identifier or "N/A",
                "checked_in_at": checkin_time,
            }
        }, status=400)

    # 5. Atomically record Attendance
    checkin_method = (
        CheckInMethod.QR_SCAN if method_str == "qr_scan" else CheckInMethod.MANUAL
    )

    try:
        with transaction.atomic():
            attendance = Attendance.objects.create(
                registration=registration,
                checked_in_by=request.user,
                method=checkin_method,
                notes=notes[:255] if notes else "",
            )
    except IntegrityError:
        return JsonResponse({
            "success": False,
            "code": "ALREADY_CHECKED_IN",
            "message": "Ticket was already used for check-in.",
        }, status=400)

    # 6. Return successful check-in
    student_profile = getattr(registration.student, "profile", None)
    student_name = (
        student_profile.display_name
        if student_profile and student_profile.display_name
        else registration.student.get_full_name() or registration.student.username
    )
    student_id = (
        student_profile.student_identifier
        if student_profile and student_profile.student_identifier
        else "N/A"
    )

    # In-app notification for student check-in
    notify(
        recipient=registration.student,
        title="Check-in Confirmed",
        message=f"Welcome to '{event.title}'! Your entry was successfully verified at {attendance.checked_in_at.strftime('%I:%M %p')}.",
        notification_type=NotificationType.INFO,
        target_url=reverse("student:ticket_detail", kwargs={"ticket_token": registration.ticket_token}),
    )

    return JsonResponse({
        "success": True,
        "code": "SUCCESS",
        "message": f"Verified: {student_name}",
        "attendee": {
            "name": student_name,
            "student_id": student_id,
            "email": registration.student.email,
            "checked_in_at": attendance.checked_in_at.strftime("%I:%M:%S %p"),
            "method": attendance.get_method_display(),
        },
        "stats": {
            "attendance_count": event.attendance_count,
            "total_confirmed": event.confirmed_registrations_count,
            "attendance_rate": event.attendance_rate,
        }
    })
