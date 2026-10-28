"""
MUJVERSE — Platform Admin URL Patterns (Phase 2 & 4 Complete)
"""

from django.urls import path
from . import views

app_name = "platform_admin"

urlpatterns = [
    path("", views.admin_dashboard_view, name="dashboard"),
    path("events/pending/", views.pending_events_view, name="pending_events"),
    path("events/<int:pk>/approve/", views.approve_event_view, name="approve_event"),
    path("events/<int:pk>/reject/", views.reject_event_view, name="reject_event"),
    path("users/", views.users_list_view, name="users"),
    path("users/<int:user_id>/toggle-status/", views.toggle_user_status_view, name="toggle_user_status"),
    path("users/<int:user_id>/approve-organizer/", views.approve_organizer_user_view, name="approve_organizer"),
    path("categories/", views.categories_admin_view, name="categories"),
    path("categories/create/", views.category_create_view, name="category_create"),
    path("categories/<int:category_id>/toggle-active/", views.category_toggle_active_view, name="category_toggle_active"),
    path("reports/", views.reports_admin_view, name="reports"),
    path("reports/<int:report_id>/resolve/", views.resolve_report_view, name="resolve_report"),
    path("reports/<int:report_id>/dismiss/", views.dismiss_report_view, name="dismiss_report"),
]
