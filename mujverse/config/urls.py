"""
MUJVERSE — URL Configuration (Root)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django built-in admin
    path("admin/", admin.site.urls),

    # Platform admin (custom)
    path("platform-admin/", include("mujverse.apps.moderation.urls", namespace="platform_admin")),

    # Public pages
    path("", include("mujverse.apps.events.public_urls", namespace="public")),

    # Accounts (auth, profile, dashboard-redirect)
    path("accounts/", include("mujverse.apps.accounts.urls", namespace="accounts")),

    # Student area
    path("student/", include("mujverse.apps.registrations.urls", namespace="student")),

    # Organizer area
    path("organizer/", include("mujverse.apps.events.organizer_urls", namespace="organizer")),

    # Notifications API
    path("notifications/", include("mujverse.apps.notifications.urls", namespace="notifications")),

    # Reviews
    path("reviews/", include("mujverse.apps.reviews.urls", namespace="reviews")),

    # Attendance / scanner
    path("attendance/", include("mujverse.apps.attendance.urls", namespace="attendance")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
