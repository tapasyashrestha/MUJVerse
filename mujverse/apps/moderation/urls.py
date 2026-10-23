"""
MUJVERSE — Platform Admin URL Patterns
"""

from django.urls import path
from . import views

app_name = "platform_admin"

urlpatterns = [
    path("", views.admin_dashboard_view, name="dashboard"),
    path("events/pending/", views.pending_events_view, name="pending_events"),
    path("users/", views.users_list_view, name="users"),
    path("categories/", views.categories_admin_view, name="categories"),
    path("reports/", views.reports_admin_view, name="reports"),
]
