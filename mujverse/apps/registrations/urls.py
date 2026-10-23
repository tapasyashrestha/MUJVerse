"""
MUJVERSE — Student Registrations & Tickets URL Configuration
"""

from django.urls import path
from . import views

app_name = "student"

urlpatterns = [
    path("dashboard/", views.student_dashboard_view, name="dashboard"),
    path("registrations/", views.student_registrations_list_view, name="registrations"),
    path("tickets/<str:ticket_token>/", views.ticket_detail_view, name="ticket_detail"),
]
