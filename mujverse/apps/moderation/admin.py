"""
MUJVERSE — Moderation Admin
Includes EventReport and read-only protected AuditLog.
"""

from django.contrib import admin
from .models import EventReport, AuditLog


@admin.register(EventReport)
class EventReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reason", "reported_by", "event", "reported_user", "status", "created_at")
    list_filter = ("status", "reason", "created_at")
    search_fields = ("reason", "description", "reported_by__username", "event__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "object_type", "object_id")
    list_filter = ("action", "object_type", "created_at")
    search_fields = ("action", "object_type", "object_id", "actor__username")
    readonly_fields = ("created_at", "actor", "action", "object_type", "object_id", "metadata")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete audit logs, preserving security integrity
        return request.user.is_superuser
