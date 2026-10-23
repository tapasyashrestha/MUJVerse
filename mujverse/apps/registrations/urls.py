"""
MUJVERSE — Student Registrations & Tickets URL Configuration
"""

from django.urls import path
from . import views

app_name = "student"

urlpatterns = [
    path("dashboard/", views.student_dashboard_view, name="dashboard"),
    path("registrations/", views.student_registrations_list_view, name="registrations"),
    path("register/<int:event_id>/", views.event_register_view, name="register_event"),
    path("tickets/<str:ticket_token>/", views.ticket_detail_view, name="ticket_detail"),
    path("tickets/<str:ticket_token>/qr/", views.ticket_qr_code_view, name="ticket_qr"),
    path("tickets/<str:ticket_token>/cancel/", views.ticket_cancel_view, name="ticket_cancel"),
]
