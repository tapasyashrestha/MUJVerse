"""
MUJVERSE — Platform Admin URL Patterns (Phase 2)
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
    path("categories/", views.categories_admin_view, name="categories"),
    path("reports/", views.reports_admin_view, name="reports"),
]
