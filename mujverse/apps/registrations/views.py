"""
MUJVERSE — Student Registrations, QR Ticketing & Dashboard Views
Phase 3 Implementation: Concurrency-safe free registration, QR generation,
ticket pass inspection, cancellation, and student metrics.
"""

import io
import qrcode
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from mujverse.apps.accounts.decorators import student_required
from mujverse.apps.events.models import Event, EventStatus
from .models import Registration, RegistrationStatus, generate_ticket_token


@login_required
def student_dashboard_view(request):
    """
    Student dashboard displaying real upcoming registrations, past events, and ticket access.
    """
    user = request.user
    now = timezone.now()

    my_registrations = Registration.objects.filter(
        student=user,
        status=RegistrationStatus.CONFIRMED,
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
    """List all registrations (active and cancelled) for the authenticated student."""
    registrations = (
        Registration.objects.filter(student=request.user)
        .select_related("event", "event__category")
        .order_by("-registered_at")
    )
    return render(request, "student/registrations.html", {"registrations": registrations})


@login_required
@require_POST
def event_register_view(request, event_id):
    """
    Registers the authenticated student for an eligible approved event.
    Enforces transactional capacity limits using select_for_update() to prevent race conditions.
    """
    user = request.user

    # Only students and administrators can register for campus events
    is_student_or_admin = (
        getattr(user, "profile", None) is None
        or user.profile.is_student
        or user.profile.is_admin
        or user.is_staff
    )
    if not is_student_or_admin:
        messages.error(request, "Organizers cannot register for student events. Use a student account.")
        return redirect("public:explore")

    with transaction.atomic():
        try:
            event = Event.objects.select_for_update().get(id=event_id)
        except Event.DoesNotExist:
            messages.error(request, "Event does not exist.")
            return redirect("public:explore")

        # 1. Check status and public visibility
        if not (event.status == EventStatus.APPROVED and event.is_published):
            messages.error(request, "This event is currently not open for registration.")
            return redirect("public:explore")

        now = timezone.now()

        # 2. Check registration deadline
        if now > event.registration_deadline:
            messages.error(
                request,
                f"Registration for '{event.title}' closed on {event.registration_deadline.strftime('%b %d, %Y %I:%M %p')}."
            )
            return redirect(event.get_absolute_url())

        # 3. Check event conclusion
        if now >= event.end_datetime:
            messages.error(request, "This event has already concluded.")
            return redirect(event.get_absolute_url())

        # 4. Check existing registration
        existing_reg = Registration.objects.filter(event=event, student=user).first()
        if existing_reg and existing_reg.status == RegistrationStatus.CONFIRMED:
            messages.info(request, "You are already registered for this event!")
            return redirect("student:ticket_detail", ticket_token=existing_reg.ticket_token)

        # 5. Concurrency-safe capacity check
        confirmed_count = Registration.objects.filter(
            event=event,
            status=RegistrationStatus.CONFIRMED
        ).count()

        if confirmed_count >= event.capacity:
            messages.error(request, f"Sorry! '{event.title}' has reached its maximum capacity of {event.capacity} seats.")
            return redirect(event.get_absolute_url())

        # 6. Re-activate previously cancelled registration or create a fresh one
        if existing_reg:
            existing_reg.status = RegistrationStatus.CONFIRMED
            existing_reg.cancelled_at = None
            existing_reg.ticket_token = generate_ticket_token()
            existing_reg.registered_at = timezone.now()
            existing_reg.save()
            registration = existing_reg
        else:
            registration = Registration.objects.create(
                event=event,
                student=user,
                status=RegistrationStatus.CONFIRMED,
            )

    messages.success(request, f"Registration confirmed! Your free ticket pass for '{event.title}' is ready.")
    return redirect("student:ticket_detail", ticket_token=registration.ticket_token)


@login_required
def ticket_detail_view(request, ticket_token):
    """
    Displays the unique QR ticket for the authenticated student.
    Guarantees user cannot view another student's ticket unless organizer or admin.
    """
    registration = get_object_or_404(
        Registration.objects.select_related("event", "student", "student__profile"),
        ticket_token=ticket_token,
    )

    user = request.user
    is_owner = registration.student_id == user.id
    is_organizer = registration.event.organizer_id == user.id
    is_admin_user = user.is_staff or (getattr(user, "profile", None) and user.profile.is_admin)

    if not (is_owner or is_organizer or is_admin_user):
        raise PermissionDenied("You do not have permission to view this ticket.")

    return render(request, "student/ticket_detail.html", {
        "registration": registration,
        "is_owner": is_owner,
    })


@login_required
def ticket_qr_code_view(request, ticket_token):
    """
    Dynamically renders a high-resolution PNG QR code encoding only the opaque ticket token.
    Never encodes passwords or personal information.
    """
    registration = get_object_or_404(
        Registration.objects.select_related("event"),
        ticket_token=ticket_token,
    )

    user = request.user
    is_owner = registration.student_id == user.id
    is_organizer = registration.event.organizer_id == user.id
    is_admin_user = user.is_staff or (getattr(user, "profile", None) and user.profile.is_admin)

    if not (is_owner or is_organizer or is_admin_user):
        raise PermissionDenied("You do not have permission to access this QR code.")

    # Generate QR Code encoding only the opaque token
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(registration.ticket_token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#070913", back_color="#ffffff")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    response = HttpResponse(image_bytes, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@login_required
@require_POST
def ticket_cancel_view(request, ticket_token):
    """
    Cancels a confirmed registration, immediately releasing event capacity.
    Enforces event cancellation policy: cannot cancel if checked in or event has concluded.
    """
    registration = get_object_or_404(
        Registration.objects.select_related("event", "student"),
        ticket_token=ticket_token,
    )

    user = request.user
    is_owner = registration.student_id == user.id
    is_admin_user = user.is_staff or (getattr(user, "profile", None) and user.profile.is_admin)

    if not (is_owner or is_admin_user):
        raise PermissionDenied("You do not have permission to cancel this registration.")

    if registration.status == RegistrationStatus.CANCELLED:
        messages.info(request, "This registration is already cancelled.")
        return redirect("student:registrations")

    if registration.is_checked_in:
        messages.error(request, "Cannot cancel a pass that has already been verified and checked in at the event.")
        return redirect("student:ticket_detail", ticket_token=registration.ticket_token)

    now = timezone.now()
    if now >= registration.event.end_datetime:
        messages.error(request, "Cannot cancel registration for an event that has already concluded.")
        return redirect("student:ticket_detail", ticket_token=registration.ticket_token)

    registration.cancel()
    messages.success(
        request,
        f"Your registration for '{registration.event.title}' has been successfully cancelled. Your seat has been released."
    )
    return redirect("student:registrations")
