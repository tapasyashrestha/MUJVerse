"""
MUJVERSE — Events & Public Views
Handles public event discovery and organizer event management shells.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from mujverse.apps.accounts.decorators import organizer_required
from .models import Category, Event, EventStatus
from mujverse.apps.registrations.models import Registration


def home_view(request):
    """
    Public landing page with hero banner, categories, and real upcoming/featured events.
    """
    now = timezone.now()
    categories = Category.objects.filter(is_active=True)[:8]
    featured_events = Event.objects.publicly_visible().filter(start_datetime__gte=now).order_by("start_datetime")[:6]
    upcoming_events = Event.objects.publicly_visible().filter(start_datetime__gte=now).order_by("start_datetime")[6:12]

    # Real platform metrics from database (no fake stats)
    total_events_hosted = Event.objects.filter(status__in=[EventStatus.APPROVED, EventStatus.COMPLETED]).count()
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
    Explore campus events with real-time search, category filter, and date ordering.
    """
    now = timezone.now()
    queryset = Event.objects.publicly_visible()

    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    status_filter = request.GET.get("status", "upcoming")
    sort_by = request.GET.get("sort", "date_asc")

    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(venue__icontains=query)
        )

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    if status_filter == "upcoming":
        queryset = queryset.filter(start_datetime__gte=now)
    elif status_filter == "past":
        queryset = queryset.filter(end_datetime__lt=now)

    if sort_by == "date_desc":
        queryset = queryset.order_by("-start_datetime")
    elif sort_by == "title":
        queryset = queryset.order_by("title")
    else:
        queryset = queryset.order_by("start_datetime")

    categories = Category.objects.filter(is_active=True)

    context = {
        "events": queryset,
        "categories": categories,
        "selected_category": category_slug,
        "search_query": query,
        "status_filter": status_filter,
        "sort_by": sort_by,
        "total_results": queryset.count(),
    }
    return render(request, "public/explore.html", context)


def event_detail_view(request, slug):
    """
    Public event detail view. Checks student registration state if authenticated.
    """
    event = get_object_or_404(Event, slug=slug)

    # Permission check for unpublished / unapproved events
    if not event.is_publicly_viewable:
        user = request.user
        is_owner = user.is_authenticated and event.organizer_id == user.id
        is_staff_user = user.is_authenticated and (user.is_staff or getattr(user, "profile", None) and user.profile.is_admin)
        if not (is_owner or is_staff_user):
            messages.error(request, "This event is currently pending review or has not been published.")
            return redirect("public:explore")

    user_registration = None
    if request.user.is_authenticated:
        user_registration = Registration.objects.filter(
            event=event,
            student=request.user,
            status="confirmed",
        ).first()

    context = {
        "event": event,
        "user_registration": user_registration,
    }
    return render(request, "public/event_detail.html", context)


def categories_view(request):
    """Browse all event categories."""
    categories = Category.objects.filter(is_active=True)
    return render(request, "public/categories.html", {"categories": categories})


def about_view(request):
    """About MUJVERSE, mission, and Manipal University Jaipur campus."""
    return render(request, "public/about.html")


def help_view(request):
    """Frequently Asked Questions and campus support resources."""
    return render(request, "public/help.html")


# ─── Organizer Views ───────────────────────────────────────
@organizer_required
def organizer_dashboard_view(request):
    """
    Organizer dashboard showing only their own real events, registrations, and attendance.
    """
    user = request.user
    my_events = Event.objects.filter(organizer=user).order_by("-created_at")

    total_events = my_events.count()
    approved_events = my_events.filter(status=EventStatus.APPROVED).count()
    pending_events = my_events.filter(status=EventStatus.PENDING_APPROVAL).count()

    # Aggregate registrations for this organizer's events
    total_registrations = Registration.objects.filter(
        event__organizer=user,
        status="confirmed",
    ).count()

    context = {
        "events": my_events[:10],
        "total_events": total_events,
        "approved_events": approved_events,
        "pending_events": pending_events,
        "total_registrations": total_registrations,
    }
    return render(request, "organizer/dashboard.html", context)
