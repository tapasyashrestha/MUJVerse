"""
Context processor for unread notifications count across all pages.
"""

from .models import Notification


def unread_notifications_count(request):
    """
    Supplies the count and recent unread notifications to the global template context.
    """
    if request.user.is_authenticated:
        unread_qs = Notification.objects.filter(recipient=request.user, is_read=False)
        return {
            "unread_notifications_count": unread_qs.count(),
            "recent_unread_notifications": unread_qs.order_by("-created_at")[:5],
        }
    return {
        "unread_notifications_count": 0,
        "recent_unread_notifications": [],
    }
