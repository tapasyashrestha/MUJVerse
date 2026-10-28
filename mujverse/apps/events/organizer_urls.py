"""
MUJVERSE — Organizer URL Patterns (Phase 2, 3 & 4 Complete)
"""

from django.urls import path
from mujverse.apps.events import views
from mujverse.apps.reviews import views as review_views

app_name = "organizer"

urlpatterns = [
    path("", views.organizer_dashboard_view, name="index"),
    path("dashboard/", views.organizer_dashboard_view, name="dashboard"),
    path("events/create/", views.event_create_view, name="event_create"),
    path("events/<int:pk>/edit/", views.event_edit_view, name="event_edit"),
    path("events/<int:pk>/submit/", views.event_submit_view, name="event_submit"),
    path("events/<int:pk>/delete/", views.event_delete_view, name="event_delete"),
    path("events/<int:pk>/attendees/", views.event_attendees_view, name="event_attendees"),
    path("events/<int:pk>/export-attendees/", views.event_export_attendees_csv_view, name="event_export_attendees"),
    path("events/<int:pk>/reviews/", review_views.organizer_event_reviews_view, name="event_reviews"),
]
