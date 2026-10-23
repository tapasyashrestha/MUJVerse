"""
MUJVERSE — Platform Moderation & Administration Views
Restricted exclusively to Administrators.
Admin event approval/rejection logic lives in events/views.py
and is imported here to keep URL routing clean.
"""

from mujverse.apps.events.views import (
    admin_dashboard_view,
    pending_events_view,
    approve_event_view,
    reject_event_view,
    users_list_view,
    categories_admin_view,
    reports_admin_view,
)

__all__ = [
    "admin_dashboard_view",
    "pending_events_view",
    "approve_event_view",
    "reject_event_view",
    "users_list_view",
    "categories_admin_view",
    "reports_admin_view",
]
