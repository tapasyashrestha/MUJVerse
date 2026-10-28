"""
MUJVERSE — Events & Public Views  (Phase 2 Complete)
Public event discovery, organizer event CRUD + submission,
and administrator moderation approval / rejection with AuditLog.
"""

import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.db.models import Q, Avg
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.text import slugify

from mujverse.apps.accounts.decorators import organizer_required, admin_required
from mujverse.apps.moderation.models import AuditLog
from mujverse.apps.registrations.models import Registration
from mujverse.apps.attendance.models import Attendance
from mujverse.apps.notifications.models import NotificationType
from mujverse.apps.notifications.services import notify
from .forms import EventForm, EventRejectForm
from .models import Category, Event, EventStatus


# ─── Public Views ──────────────────────────────────────────────────────────────

def home_view(request):
    """
    Public landing page with hero banner, categories, and real upcoming/featured events.
    """
    now = timezone.now()
    categories = Category.objects.filter(is_active=True)[:8]
    featured_events = (
        Event.objects.publicly_visible()
        .filter(start_datetime__gte=now)
        .order_by("start_datetime")[:6]
    )
    upcoming_events = (
        Event.objects.publicly_visible()
        .filter(start_datetime__gte=now)
        .order_by("start_datetime")[6:12]
    )

    total_events_hosted = Event.objects.filter(
        status__in=[EventStatus.APPROVED, EventStatus.COMPLETED]
    ).count()
    total_registrations = Registration.objects.filter(status="confirmed").count()
    active_categories_count = Category.objects.filter(is_active=True).count()

    context = {
        "categories": categories,
        "featured_events": featured_events,
        "upcoming_events": upcoming_events,
        "total_events_hosted": total_events_hosted,
        "total_registrations": total_registrations,
        "active_categories_count": active_categories_count,
    }
    return render(request, "public/home.html", context)


def explore_view(request):
    """
    Explore campus events: search, category filter, date filter, availability,
    sorting, and pagination (12 per page).
    """
    now = timezone.now()
    queryset = Event.objects.publicly_visible().select_related("category", "organizer")

    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    date_filter = request.GET.get("date") or request.GET.get("status", "upcoming")
    if date_filter not in ["upcoming", "past", "all"]:
        date_filter = "upcoming"
    avail_filter = request.GET.get("avail", "all").strip()
    if avail_filter not in ["all", "open", "full"]:
        avail_filter = "all"
    sort_by = request.GET.get("sort", "date_asc").strip()

    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(venue__icontains=query)
        )

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    if date_filter == "upcoming":
        queryset = queryset.filter(start_datetime__gte=now)
    elif date_filter == "past":
        queryset = queryset.filter(end_datetime__lt=now)

    if sort_by == "date_desc":
        queryset = queryset.order_by("-start_datetime")
    elif sort_by == "title":
        queryset = queryset.order_by("title")
    else:  # date_asc (default)
        queryset = queryset.order_by("start_datetime")

    total_before_avail = queryset.count()

    # Availability filter is in-Python because it depends on dynamic seat counts
    all_events_list = list(queryset)
    if avail_filter == "open":
        all_events_list = [e for e in all_events_list if e.is_registration_open]
    elif avail_filter == "full":
        all_events_list = [e for e in all_events_list if e.is_full]

    paginator = Paginator(all_events_list, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = Category.objects.filter(is_active=True)

    context = {
        "page_obj": page_obj,
        "events": page_obj,
        "categories": categories,
        "selected_category": category_slug,
        "search_query": query,
        "date_filter": date_filter,
        "status_filter": date_filter,
        "avail_filter": avail_filter,
        "sort_by": sort_by,
        "total_results": len(all_events_list),
    }
    return render(request, "public/explore.html", context)


def event_detail_view(request, slug):
    """
    Public event detail view. Checks student registration state if authenticated.
    Non-public events are only visible to the owning organizer or platform admins.
    """
    event = get_object_or_404(Event, slug=slug)

    if not event.is_publicly_viewable:
        user = request.user
        is_owner = user.is_authenticated and event.organizer_id == user.id
        is_staff_user = user.is_authenticated and (
            user.is_staff
            or (getattr(user, "profile", None) and user.profile.is_admin)
        )
        if not (is_owner or is_staff_user):
            messages.error(request, "This event is currently pending review or has not been published.")
            return redirect("public:explore")

    user_registration = None
    user_cancelled_registration = None
    if request.user.is_authenticated:
        user_registration = Registration.objects.filter(
            event=event,
            student=request.user,
            status="confirmed",
        ).first()
        if not user_registration:
            user_cancelled_registration = Registration.objects.filter(
                event=event,
                student=request.user,
                status="cancelled",
            ).first()

    from mujverse.apps.reviews.models import Review
    from mujverse.apps.reviews.views import can_user_review_event

    reviews = (
        Review.objects.filter(event=event, is_visible=True)
        .select_related("student", "student__profile")
        .order_by("-created_at")[:10]
    )
    avg_rating = Review.objects.filter(event=event, is_visible=True).aggregate(Avg("rating"))["rating__avg"]
    can_review, _ = can_user_review_event(request.user, event) if request.user.is_authenticated else (False, "")
    user_review = (
        Review.objects.filter(event=event, student=request.user).first()
        if request.user.is_authenticated
        else None
    )

    context = {
        "event": event,
        "user_registration": user_registration,
        "user_cancelled_registration": user_cancelled_registration,
        "reviews": reviews,
        "avg_rating": round(avg_rating, 1) if avg_rating else None,
        "can_review": can_review,
        "user_review": user_review,
    }
    return render(request, "public/event_detail.html", context)


def categories_view(request):
    """Browse all active event categories with event counts."""
    categories = Category.objects.filter(is_active=True)
    return render(request, "public/categories.html", {"categories": categories})


def about_view(request):
    """About MUJVERSE — mission, institution, and team."""
    return render(request, "public/about.html")


def help_view(request):
    """Frequently Asked Questions and campus support resources."""
    return render(request, "public/help.html")


# ─── Organizer Views ───────────────────────────────────────────────────────────

@organizer_required
def organizer_dashboard_view(request):
    """
    Organizer dashboard — real database metrics, chart data, own events list with state,
    attendance totals, and attendee feedback.
    """
    user = request.user
    my_events = Event.objects.filter(organizer=user).select_related("category").order_by("-created_at")

    total_events = my_events.count()
    approved_events = my_events.filter(status=EventStatus.APPROVED).count()
    pending_events = my_events.filter(status=EventStatus.PENDING_APPROVAL).count()
    rejected_events = my_events.filter(status=EventStatus.REJECTED).count()

    total_registrations = Registration.objects.filter(
        event__organizer=user,
        status="confirmed",
    ).count()

    total_attendance = Attendance.objects.filter(
        registration__event__organizer=user
    ).count()

    overall_attendance_rate = (
        round((total_attendance / total_registrations) * 100, 1)
        if total_registrations > 0
        else 0.0
    )

    # Database-backed Chart.js series for organizer's top active events
    chart_events = list(my_events.filter(status__in=[EventStatus.APPROVED, EventStatus.COMPLETED])[:6])
    chart_labels = [e.title[:18] + ("…" if len(e.title) > 18 else "") for e in chart_events]
    chart_registrations = [e.confirmed_registrations_count for e in chart_events]
    chart_capacities = [e.capacity for e in chart_events]
    chart_attendances = [e.attendance_count for e in chart_events]

    from mujverse.apps.reviews.models import Review
    recent_reviews = (
        Review.objects.filter(event__organizer=user)
        .select_related("event", "student", "student__profile")
        .order_by("-created_at")[:5]
    )

    context = {
        "events": my_events[:20],
        "total_events": total_events,
        "approved_events": approved_events,
        "pending_events": pending_events,
        "rejected_events": rejected_events,
        "total_registrations": total_registrations,
        "total_attendance": total_attendance,
        "overall_attendance_rate": overall_attendance_rate,
        "chart_labels": chart_labels,
        "chart_registrations": chart_registrations,
        "chart_capacities": chart_capacities,
        "chart_attendances": chart_attendances,
        "recent_reviews": recent_reviews,
    }
    return render(request, "organizer/dashboard.html", context)


@organizer_required
def event_create_view(request):
    """
    Create a new event draft. Assigns the authenticated organizer and saves as draft.
    Optionally submits for approval immediately if the organizer clicks 'Submit'.
    """
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.status = EventStatus.DRAFT
            event.save()

            action = request.POST.get("action", "save")
            if action == "submit":
                return _submit_event_for_approval(request, event)

            messages.success(request, f'Event "{event.title}" saved as draft. You can submit it for approval when ready.')
            return redirect("organizer:event_edit", pk=event.pk)
    else:
        form = EventForm()

    return render(request, "organizer/event_form.html", {"form": form, "action": "Create"})


@organizer_required
def event_edit_view(request, pk):
    """
    Edit an existing draft or rejected event owned by the organizer.
    Approved / pending events cannot be edited until rejected or cancelled.
    """
    event = get_object_or_404(Event, pk=pk)

    # Ownership enforcement
    if event.organizer != request.user:
        messages.error(request, "You do not have permission to edit this event.")
        return redirect("organizer:dashboard")

    # Only draft and rejected events can be edited
    if event.status not in [EventStatus.DRAFT, EventStatus.REJECTED]:
        messages.warning(
            request,
            f"This event is currently {event.get_status_display()} and cannot be edited. "
            "Contact platform admin if changes are urgent.",
        )
        return redirect("organizer:dashboard")

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            saved_event = form.save(commit=False)
            # Reset rejection info if organizer re-edits a rejected event
            if event.status == EventStatus.REJECTED:
                saved_event.rejection_reason = ""
            saved_event.save()

            action = request.POST.get("action", "save")
            if action == "submit":
                return _submit_event_for_approval(request, saved_event)

            messages.success(request, f'Event "{saved_event.title}" updated successfully.')
            return redirect("organizer:event_edit", pk=saved_event.pk)
    else:
        form = EventForm(instance=event)

    return render(request, "organizer/event_form.html", {
        "form": form,
        "event": event,
        "action": "Edit",
    })


def _submit_event_for_approval(request, event):
    """
    Internal helper: transition an event from draft/rejected → pending_approval.
    """
    event.status = EventStatus.PENDING_APPROVAL
    event.rejection_reason = ""
    event.save(update_fields=["status", "rejection_reason"])

    notify(
        recipient=event.organizer,
        title="Event Submitted",
        message=f"'{event.title}' was submitted for administrative review. You will receive an alert upon approval.",
        notification_type=NotificationType.INFO,
        target_url=reverse("organizer:dashboard"),
    )

    messages.success(
        request,
        f'"{event.title}" has been submitted for administrator approval. '
        "You will be notified once a decision is made.",
    )
    return redirect("organizer:dashboard")


@organizer_required
def event_submit_view(request, pk):
    """
    POST-only: submit a draft or rejected event for approval.
    Ownership enforced server-side.
    """
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if event.status not in [EventStatus.DRAFT, EventStatus.REJECTED]:
        messages.error(request, "This event cannot be submitted in its current state.")
        return redirect("organizer:dashboard")

    return _submit_event_for_approval(request, event)


@organizer_required
def event_delete_view(request, pk):
    """
    Organizer-only: delete a draft event. Approved events cannot be deleted.
    """
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if event.status not in [EventStatus.DRAFT, EventStatus.REJECTED]:
        messages.error(request, "Only draft or rejected events can be deleted.")
        return redirect("organizer:dashboard")

    if request.method == "POST":
        title = event.title
        event.delete()
        messages.success(request, f'Event "{title}" has been deleted.')
        return redirect("organizer:dashboard")

    return render(request, "organizer/event_confirm_delete.html", {"event": event})


# ─── Administrator Moderation Views ────────────────────────────────────────────

@admin_required
def admin_dashboard_view(request):
    """
    Platform administrator dashboard with real system metrics and pending actions.
    """
    from django.contrib.auth.models import User
    from mujverse.apps.attendance.models import Attendance
    from mujverse.apps.moderation.models import EventReport

    total_users = User.objects.count()
    student_users = User.objects.filter(profile__role="student").count()
    organizer_users = User.objects.filter(profile__role="organizer").count()

    pending_events = Event.objects.filter(
        status=EventStatus.PENDING_APPROVAL
    ).select_related("organizer", "category")
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
    events = (
        Event.objects.filter(status=EventStatus.PENDING_APPROVAL)
        .select_related("organizer", "category")
        .order_by("-created_at")
    )
    return render(request, "admin_dashboard/pending_events.html", {"events": events})


@admin_required
def approve_event_view(request, pk):
    """
    POST-only. Approve a pending event: set status=APPROVED, is_published=True,
    and write an AuditLog record.
    """
    event = get_object_or_404(Event, pk=pk)

    if event.status != EventStatus.PENDING_APPROVAL:
        messages.error(request, f'Event "{event.title}" is not pending approval.')
        return redirect("platform_admin:pending_events")

    if request.method == "POST":
        event.status = EventStatus.APPROVED
        event.is_published = True
        event.rejection_reason = ""
        event.save(update_fields=["status", "is_published", "rejection_reason"])

        AuditLog.log(
            actor=request.user,
            action="event_approved",
            object_type="Event",
            object_id=event.pk,
            metadata={
                "event_title": event.title,
                "organizer": event.organizer.username,
            },
        )

        notify(
            recipient=event.organizer,
            title="Event Approved!",
            message=f"Congratulations! Your event '{event.title}' has been approved and is now live on MUJVERSE.",
            notification_type=NotificationType.APPROVAL,
            target_url=event.get_absolute_url(),
            send_email=True,
        )

        messages.success(
            request,
            f'"{event.title}" has been approved and is now publicly visible.',
        )
    return redirect("platform_admin:pending_events")


@admin_required
def reject_event_view(request, pk):
    """
    GET — Show rejection-reason form.
    POST — Validate reason, set status=REJECTED, clear publication, write AuditLog.
    """
    event = get_object_or_404(Event, pk=pk)

    if event.status != EventStatus.PENDING_APPROVAL:
        messages.error(request, f'Event "{event.title}" is not pending approval.')
        return redirect("platform_admin:pending_events")

    if request.method == "POST":
        form = EventRejectForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data["rejection_reason"]
            event.status = EventStatus.REJECTED
            event.is_published = False
            event.rejection_reason = reason
            event.save(update_fields=["status", "is_published", "rejection_reason"])

            AuditLog.log(
                actor=request.user,
                action="event_rejected",
                object_type="Event",
                object_id=event.pk,
                metadata={
                    "event_title": event.title,
                    "organizer": event.organizer.username,
                    "reason": reason,
                },
            )

            notify(
                recipient=event.organizer,
                title="Event Changes Requested",
                message=f"Your event '{event.title}' was reviewed and requires revision: {reason}",
                notification_type=NotificationType.REJECTION,
                target_url=reverse("organizer:event_edit", kwargs={"pk": event.pk}),
                send_email=True,
            )

            messages.warning(
                request,
                f'"{event.title}" has been rejected. The organizer has been notified.',
            )
            return redirect("platform_admin:pending_events")
    else:
        form = EventRejectForm()

    return render(request, "admin_dashboard/reject_event.html", {
        "event": event,
        "form": form,
    })


@admin_required
def users_list_view(request):
    """User management view for administrators with search and role filters."""
    from django.contrib.auth.models import User
    users = User.objects.select_related("profile").order_by("-date_joined")

    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__display_name__icontains=query)
            | Q(profile__student_identifier__icontains=query)
        )

    if role_filter in ["student", "organizer", "admin"]:
        users = users.filter(profile__role=role_filter)

    return render(request, "admin_dashboard/users.html", {
        "users_list": users[:100],
        "query": query,
        "role_filter": role_filter,
        "total_count": users.count(),
    })


@admin_required
@require_POST
def toggle_user_status_view(request, user_id):
    """
    Administrator action to suspend or reactivate a user account.
    Prevents self-suspension and unauthorized superuser alteration.
    Logs action to AuditLog.
    """
    from django.contrib.auth.models import User
    target_user = get_object_or_404(User, id=user_id)

    if target_user.id == request.user.id:
        messages.error(request, "Security constraint: You cannot suspend your own account.")
        return redirect("platform_admin:users")

    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, "Permission denied: Only superusers can modify other superusers.")
        return redirect("platform_admin:users")

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=["is_active"])

    action_str = "user_reactivated" if target_user.is_active else "user_suspended"
    AuditLog.log(
        actor=request.user,
        action=action_str,
        object_type="User",
        object_id=target_user.id,
        metadata={"username": target_user.username, "new_active_status": target_user.is_active},
    )

    state = "reactivated" if target_user.is_active else "suspended"
    messages.success(request, f"User account '{target_user.username}' has been {state}.")
    return redirect("platform_admin:users")


@admin_required
@require_POST
def approve_organizer_user_view(request, user_id):
    """
    Administrator action to verify and approve a pending Club Organizer account.
    Activates organizer privileges and approves associated club memberships.
    """
    from django.contrib.auth.models import User
    from mujverse.apps.accounts.models import Profile, AccountStatus, RoleChoices, ClubMembership, ApprovalStatus

    target_user = get_object_or_404(User, id=user_id)
    profile = getattr(target_user, "profile", None)

    if not profile or profile.role != RoleChoices.ORGANIZER:
        messages.error(request, "Target user is not registered as an organizer.")
        return redirect("platform_admin:users")

    profile.status = AccountStatus.ACTIVE
    profile.save(update_fields=["status", "updated_at"])

    # Approve pending club membership and club if needed
    for m in ClubMembership.objects.filter(user=target_user):
        m.approval_status = ApprovalStatus.APPROVED
        m.reviewed_by = request.user
        m.save()
        if m.club.verification_status == ApprovalStatus.PENDING:
            m.club.verification_status = ApprovalStatus.APPROVED
            m.club.save(update_fields=["verification_status", "updated_at"])

    AuditLog.log(
        actor=request.user,
        action="organizer_approved",
        object_type="User",
        object_id=target_user.id,
        metadata={"username": target_user.username, "organizer": profile.display_name},
    )

    messages.success(request, f"Organizer '{target_user.username}' ({profile.display_name}) has been approved!")
    return redirect("platform_admin:users")


@admin_required
def categories_admin_view(request):
    """Category management view with event counts and active toggle."""
    categories = Category.objects.all().order_by("name")
    return render(request, "admin_dashboard/categories.html", {"categories": categories})


@admin_required
@require_POST
def category_create_view(request):
    """Creates a new event category and logs audit record."""
    name = request.POST.get("name", "").strip()
    icon = request.POST.get("icon", "bi-calendar-event").strip()

    if not name:
        messages.error(request, "Category name is required.")
        return redirect("platform_admin:categories")

    category = Category.objects.create(name=name, icon=icon or "bi-calendar-event", is_active=True)
    AuditLog.log(
        actor=request.user,
        action="category_created",
        object_type="Category",
        object_id=category.id,
        metadata={"name": category.name, "slug": category.slug},
    )
    messages.success(request, f"Category '{category.name}' created successfully.")
    return redirect("platform_admin:categories")


@admin_required
@require_POST
def category_toggle_active_view(request, category_id):
    """Toggles active/inactive status of a category."""
    category = get_object_or_404(Category, id=category_id)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active"])

    AuditLog.log(
        actor=request.user,
        action="category_updated",
        object_type="Category",
        object_id=category.id,
        metadata={"name": category.name, "is_active": category.is_active},
    )
    status_str = "activated" if category.is_active else "deactivated"
    messages.success(request, f"Category '{category.name}' has been {status_str}.")
    return redirect("platform_admin:categories")


@admin_required
def reports_admin_view(request):
    """Content reports moderation queue with status filter."""
    from mujverse.apps.moderation.models import EventReport
    reports = EventReport.objects.select_related(
        "reported_by", "event", "reported_user"
    ).order_by("-created_at")

    status_filter = request.GET.get("status", "open").strip()
    if status_filter != "all":
        reports = reports.filter(status=status_filter)

    return render(request, "admin_dashboard/reports.html", {
        "reports": reports,
        "status_filter": status_filter,
    })


@admin_required
@require_POST
def resolve_report_view(request, report_id):
    """Resolves an open report and logs audit trail."""
    from mujverse.apps.moderation.models import EventReport, ReportStatus
    report = get_object_or_404(EventReport, id=report_id)
    notes = request.POST.get("notes", "").strip() or "Resolved by administrator."

    report.status = ReportStatus.RESOLVED
    report.reviewed_by = request.user
    report.resolution_notes = notes
    report.save(update_fields=["status", "reviewed_by", "resolution_notes", "updated_at"])

    AuditLog.log(
        actor=request.user,
        action="report_resolved",
        object_type="EventReport",
        object_id=report.id,
        metadata={"resolution_notes": notes},
    )
    messages.success(request, f"Report #{report.id} marked as resolved.")
    return redirect("platform_admin:reports")


@admin_required
@require_POST
def dismiss_report_view(request, report_id):
    """Dismisses a report and logs audit trail."""
    from mujverse.apps.moderation.models import EventReport, ReportStatus
    report = get_object_or_404(EventReport, id=report_id)
    notes = request.POST.get("notes", "").strip() or "Dismissed by administrator."

    report.status = ReportStatus.DISMISSED
    report.reviewed_by = request.user
    report.resolution_notes = notes
    report.save(update_fields=["status", "reviewed_by", "resolution_notes", "updated_at"])

    AuditLog.log(
        actor=request.user,
        action="report_dismissed",
        object_type="EventReport",
        object_id=report.id,
        metadata={"resolution_notes": notes},
    )
    messages.info(request, f"Report #{report.id} dismissed.")
    return redirect("platform_admin:reports")


# ─── Attendee Management & CSV Export (Phase 3) ────────────────────────────────

def sanitize_csv_cell(val):
    """Prevent spreadsheet formula injection by quoting unsafe leading characters."""
    if val is None:
        return ""
    s = str(val).strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


@login_required
def event_attendees_view(request, pk):
    """
    Displays the attendee list, check-in status, and statistics for an authorized organizer or admin.
    """
    event = get_object_or_404(Event, pk=pk)

    is_owner = event.organizer_id == request.user.id
    is_admin = request.user.is_staff or (getattr(request.user, "profile", None) and request.user.profile.is_admin)
    if not (is_owner or is_admin):
        raise PermissionDenied("You can only view attendee records for your own events.")

    registrations = (
        Registration.objects.filter(event=event)
        .select_related("student", "student__profile", "attendance", "attendance__checked_in_by")
        .order_by("-registered_at")
    )

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all").strip()

    if query:
        registrations = registrations.filter(
            Q(student__username__icontains=query)
            | Q(student__email__icontains=query)
            | Q(student__profile__display_name__icontains=query)
            | Q(student__profile__student_identifier__icontains=query)
        )

    if status_filter == "checked_in":
        registrations = registrations.filter(attendance__isnull=False)
    elif status_filter == "not_checked_in":
        registrations = registrations.filter(status="confirmed", attendance__isnull=True)
    elif status_filter == "confirmed":
        registrations = registrations.filter(status="confirmed")
    elif status_filter == "cancelled":
        registrations = registrations.filter(status="cancelled")

    context = {
        "event": event,
        "registrations": registrations,
        "total_registrations": registrations.count(),
        "query": query,
        "status_filter": status_filter,
    }
    return render(request, "organizer/attendees.html", context)


@login_required
def event_export_attendees_csv_view(request, pk):
    """
    Exports the attendee list to CSV with protections against spreadsheet formula injection.
    Only authorized organizers and administrators can export.
    """
    event = get_object_or_404(Event, pk=pk)

    is_owner = event.organizer_id == request.user.id
    is_admin = request.user.is_staff or (getattr(request.user, "profile", None) and request.user.profile.is_admin)
    if not (is_owner or is_admin):
        raise PermissionDenied("You can only export attendee records for your own events.")

    registrations = (
        Registration.objects.filter(event=event)
        .select_related("student", "student__profile", "attendance", "attendance__checked_in_by")
        .order_by("registered_at")
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    safe_slug = slugify(event.title) or "event"
    response["Content-Disposition"] = f'attachment; filename="attendees_{safe_slug}_{event.id}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Attendee Name",
        "Student Identifier",
        "Registration Date",
        "Registration Status",
        "Checked In",
        "Check-in Time",
        "Check-in Method",
        "Verified By",
    ])

    for reg in registrations:
        profile = getattr(reg.student, "profile", None)
        name = (
            profile.display_name
            if profile and profile.display_name
            else reg.student.get_full_name() or reg.student.username
        )
        student_id = (
            profile.student_identifier
            if profile and profile.student_identifier
            else "N/A"
        )
        is_checked_in = hasattr(reg, "attendance")
        checkin_time = (
            reg.attendance.checked_in_at.strftime("%Y-%m-%d %H:%M:%S")
            if is_checked_in
            else "N/A"
        )
        checkin_method = reg.attendance.get_method_display() if is_checked_in else "N/A"
        verified_by = (
            reg.attendance.checked_in_by.username
            if is_checked_in and reg.attendance.checked_in_by
            else "N/A"
        )

        row = [
            sanitize_csv_cell(name),
            sanitize_csv_cell(student_id),
            sanitize_csv_cell(reg.registered_at.strftime("%Y-%m-%d %H:%M:%S")),
            sanitize_csv_cell(reg.get_status_display()),
            sanitize_csv_cell("Yes" if is_checked_in else "No"),
            sanitize_csv_cell(checkin_time),
            sanitize_csv_cell(checkin_method),
            sanitize_csv_cell(verified_by),
        ]
        writer.writerow(row)

    return response

