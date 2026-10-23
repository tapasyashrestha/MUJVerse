"""
MUJVERSE — Organizer URL Patterns
"""

from django.urls import path
from . import views

app_name = "organizer"

urlpatterns = [
    path("dashboard/", views.organizer_dashboard_view, name="dashboard"),
    # Additional event management endpoints will be completed in Phase 3
]
