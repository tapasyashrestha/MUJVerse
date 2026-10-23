"""
MUJVERSE — Organizer URL Patterns (Phase 2 & 3 Complete)
"""

from django.urls import path
from mujverse.apps.events import views

app_name = "organizer"

urlpatterns = [
    path("dashboard/", views.organizer_dashboard_view, name="dashboard"),
    path("events/create/", views.event_create_view, name="event_create"),
    path("events/<int:pk>/edit/", views.event_edit_view, name="event_edit"),
    path("events/<int:pk>/submit/", views.event_submit_view, name="event_submit"),
    path("events/<int:pk>/delete/", views.event_delete_view, name="event_delete"),
    path("events/<int:pk>/attendees/", views.event_attendees_view, name="event_attendees"),
    path("events/<int:pk>/export-attendees/", views.event_export_attendees_csv_view, name="event_export_attendees"),
]
