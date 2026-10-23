"""
MUJVERSE — Attendance Admin
"""

from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "student_name",
        "event_title",
        "method",
        "checked_in_by",
        "checked_in_at",
    )
    list_filter = ("method", "checked_in_at")
    search_fields = (
        "registration__student__username",
        "registration__event__title",
        "registration__ticket_token",
    )
    readonly_fields = ("checked_in_at",)

    def student_name(self, obj):
        return obj.registration.student.get_full_name() or obj.registration.student.username
    student_name.short_description = "Student"

    def event_title(self, obj):
        return obj.registration.event.title
    event_title.short_description = "Event"
