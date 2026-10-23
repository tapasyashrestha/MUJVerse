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
    toggle_user_status_view,
    categories_admin_view,
    category_create_view,
    category_toggle_active_view,
    reports_admin_view,
    resolve_report_view,
    dismiss_report_view,
)

__all__ = [
    "admin_dashboard_view",
    "pending_events_view",
    "approve_event_view",
    "reject_event_view",
    "users_list_view",
    "toggle_user_status_view",
    "categories_admin_view",
    "category_create_view",
    "category_toggle_active_view",
    "reports_admin_view",
    "resolve_report_view",
    "dismiss_report_view",
]
