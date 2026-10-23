"""
MUJVERSE — Authentication & Profile Views
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.urls import reverse_lazy
from .forms import StudentRegistrationForm, UserLoginForm, UserProfileUpdateForm
from .models import RoleChoices


@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    Public registration view for MUJ students.
    Creates a student account with hashed password and associated Profile.
    """
    if request.user.is_authenticated:
        return redirect("accounts:dashboard_redirect")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to MUJVERSE, {user.first_name or user.username}! Your student account is now active.",
            )
            return redirect("accounts:dashboard_redirect")
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = StudentRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Secure login using Django session authentication.
    Redirects to user-specific dashboard based on role.
    """
    if request.user.is_authenticated:
        return redirect("accounts:dashboard_redirect")

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect("accounts:dashboard_redirect")
        else:
            messages.error(request, "Invalid username/student ID or password.")
    else:
        form = UserLoginForm()

    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Terminates the user session and flushes session data.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been logged out successfully.")
    return redirect("public:home")


@login_required
def dashboard_redirect_view(request):
    """
    Central router that directs authenticated users to their role-specific dashboard.
    """
    user = request.user
    profile = getattr(user, "profile", None)

    if user.is_superuser or (profile and profile.is_admin):
        return redirect("platform_admin:dashboard")
    elif profile and profile.is_organizer:
        return redirect("organizer:dashboard")
    else:
        return redirect("student:dashboard")


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """
    Displays and allows editing of personal profile information.
    Role and staff privileges cannot be altered here.
    """
    profile = getattr(request.user, "profile", None)
    if request.method == "POST":
        form = UserProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("accounts:profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserProfileUpdateForm(instance=profile, user=request.user)

    return render(request, "accounts/profile.html", {"form": form, "profile": profile})


# ─── Password Reset Views ─────────────────────────────────
class CustomPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
