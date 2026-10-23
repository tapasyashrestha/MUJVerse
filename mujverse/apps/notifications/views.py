"""
MUJVERSE — Notifications API & Views
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notifications_list_view(request):
    """View all notifications for the authenticated user."""
    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    return render(request, "student/notifications.html", {"notifications": notifications})


@login_required
def unread_count_api(request):
    """JSON API endpoint returning unread notification count for the current user."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({"unread_count": count})


@login_required
@require_POST
def mark_notification_read_view(request, pk):
    """Mark a single notification as read (JSON/Fetch or form POST)."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept", "").find("application/json") != -1 or request.content_type == "application/json":
        return JsonResponse({"success": True, "message": "Notification marked as read.", "id": pk})
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read_view(request):
    """Mark all unread notifications as read (JSON/Fetch or form POST)."""
    updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept", "").find("application/json") != -1 or request.content_type == "application/json":
        return JsonResponse({"success": True, "message": "All notifications marked as read.", "updated": updated_count})
    return redirect("notifications:list")
