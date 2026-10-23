"""
MUJVERSE — Attendance URL Patterns
"""

from django.urls import path
from . import views

app_name = "attendance"

urlpatterns = [
    path("scanner/<int:event_id>/", views.scanner_view, name="scanner"),
    path("verify/<int:event_id>/", views.verify_checkin_api, name="verify_checkin"),
]
