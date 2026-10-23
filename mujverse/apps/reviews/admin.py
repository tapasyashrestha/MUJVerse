"""
MUJVERSE — Reviews Admin
"""

from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("student", "event", "rating", "is_visible", "created_at")
    list_filter = ("rating", "is_visible", "created_at")
    search_fields = ("student__username", "event__title", "comment")
    actions = ["hide_reviews", "show_reviews"]

    @admin.action(description="Hide selected reviews")
    def hide_reviews(self, request, queryset):
        queryset.update(is_visible=False)

    @admin.action(description="Make selected reviews visible")
    def show_reviews(self, request, queryset):
        queryset.update(is_visible=True)
