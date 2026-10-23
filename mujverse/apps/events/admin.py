"""
MUJVERSE — Events Admin
Configures Category and Event models with search, filters, and moderation actions.
"""

from django.contrib import admin
from .models import Category, Event, EventStatus
from mujverse.apps.moderation.models import AuditLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "is_active", "events_count", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    def events_count(self, obj):
        return obj.events.count()
    events_count.short_description = "Events"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "organizer",
        "status",
        "is_published",
        "start_datetime",
        "capacity",
        "confirmed_count",
    )
    list_filter = ("status", "is_published", "category", "start_datetime")
    search_fields = ("title", "description", "venue", "organizer__username")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    actions = ["approve_events", "reject_events", "publish_events"]

    def confirmed_count(self, obj):
        return obj.confirmed_registrations_count
    confirmed_count.short_description = "Registered"

    @admin.action(description="Approve selected events")
    def approve_events(self, request, queryset):
        count = queryset.update(status=EventStatus.APPROVED)
        for event in queryset:
            AuditLog.log(request.user, "event_approved", "Event", event.id, {"title": event.title})
        self.message_user(request, f"{count} event(s) successfully approved.")

    @admin.action(description="Reject selected events")
    def reject_events(self, request, queryset):
        count = queryset.update(status=EventStatus.REJECTED)
        for event in queryset:
            AuditLog.log(request.user, "event_rejected", "Event", event.id, {"title": event.title})
        self.message_user(request, f"{count} event(s) marked as rejected.")

    @admin.action(description="Publish approved events")
    def publish_events(self, request, queryset):
        approved = queryset.filter(status=EventStatus.APPROVED)
        count = approved.update(is_published=True)
        self.message_user(request, f"{count} approved event(s) set to publicly visible.")
