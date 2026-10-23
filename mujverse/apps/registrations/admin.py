"""
MUJVERSE — Registrations Admin
"""

from django.contrib import admin
from .models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_token_short",
        "event",
        "student",
        "status",
        "is_attended",
        "registered_at",
    )
    list_filter = ("status", "registered_at", "event__category")
    search_fields = (
        "ticket_token",
        "student__username",
        "student__email",
        "student__profile__student_identifier",
        "event__title",
    )
    readonly_fields = ("ticket_token", "registered_at", "cancelled_at")

    def ticket_token_short(self, obj):
        return f"{obj.ticket_token[:8]}…"
    ticket_token_short.short_description = "Ticket Token"

    def is_attended(self, obj):
        return obj.is_checked_in
    is_attended.boolean = True
    is_attended.short_description = "Checked In"
