"""
MUJVERSE — Accounts URL Configuration
"""

from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("dashboard-redirect/", views.dashboard_redirect_view, name="dashboard_redirect"),
    path("demo-organizer/", views.demo_login_organizer_view, name="demo_login_organizer"),
    path("demo-student/", views.demo_login_student_view, name="demo_login_student"),

    # Password Reset
    path("password-reset/", views.CustomPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
