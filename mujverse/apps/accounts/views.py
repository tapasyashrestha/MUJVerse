"""
MUJVERSE — Authentication & Profile Views
Supports dynamic student/organizer registration, dual email/regno login, and approval workflow.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.urls import reverse_lazy, reverse
from django.contrib.auth.models import User
from .forms import (
    StudentRegistrationForm,
    OrganizerRegistrationForm,
    UserLoginForm,
    UserProfileUpdateForm,
)
from .models import RoleChoices, AccountStatus, ClubMembership


@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    Public registration view with dynamic role selection (Student vs. Club Organizer).
    Supports standard POST and Fetch/AJAX JSON submission.
    """
    if request.user.is_authenticated:
        return redirect("accounts:dashboard_redirect")

    selected_role = request.GET.get("role", "student")
    if selected_role not in ["student", "organizer"]:
        selected_role = "student"

    if request.method == "POST":
        role = request.POST.get("registration_role", "student")
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.content_type == "application/json"

        if role == "organizer":
            form = OrganizerRegistrationForm(request.POST)
            if form.is_valid():
                user = form.save()
                login(request, user)
                if is_ajax:
                    return JsonResponse({
                        "success": True,
                        "message": "Organizer registration submitted! Your account is pending administrator verification.",
                        "redirect_url": reverse("accounts:pending_approval"),
                    })
                messages.info(
                    request,
                    f"Welcome to MUJVERSE, {user.first_name or user.username}! "
                    "Your Club Organizer account is currently pending administrative approval. "
                    "You will receive full event creation access once verified.",
                )
                return redirect("accounts:pending_approval")
            else:
                if is_ajax:
                    return JsonResponse({"success": False, "errors": form.errors}, status=400)
                messages.error(request, "Please correct the errors in the organizer registration form.")
                student_form = StudentRegistrationForm()
                return render(request, "accounts/register.html", {
                    "selected_role": "organizer",
                    "student_form": student_form,
                    "organizer_form": form,
                })
        else:
            form = StudentRegistrationForm(request.POST)
            if form.is_valid():
                user = form.save()
                login(request, user)
                if is_ajax:
                    return JsonResponse({
                        "success": True,
                        "message": f"Welcome to MUJVERSE, {user.first_name or user.username}! Your student account is now active.",
                        "redirect_url": reverse("accounts:dashboard_redirect"),
                    })
                messages.success(
                    request,
                    f"Welcome to MUJVERSE, {user.first_name or user.username}! Your student account is now active.",
                )
                return redirect("accounts:dashboard_redirect")
            else:
                if is_ajax:
                    return JsonResponse({"success": False, "errors": form.errors}, status=400)
                messages.error(request, "Please correct the errors in the student registration form.")
                organizer_form = OrganizerRegistrationForm()
                return render(request, "accounts/register.html", {
                    "selected_role": "student",
                    "student_form": form,
                    "organizer_form": organizer_form,
                })

    student_form = StudentRegistrationForm()
    organizer_form = OrganizerRegistrationForm()

    return render(request, "accounts/register.html", {
        "selected_role": selected_role,
        "student_form": student_form,
        "organizer_form": organizer_form,
    })


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Secure login using Email or Registration Number + Password.
    Supports standard POST and Fetch/AJAX JSON submission.
    """
    if request.user.is_authenticated:
        return redirect("accounts:dashboard_redirect")

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.content_type == "application/json"

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get("next") or request.POST.get("next")
            redirect_target = next_url if (next_url and next_url.startswith("/")) else reverse("accounts:dashboard_redirect")
            
            if is_ajax:
                return JsonResponse({"success": True, "redirect_url": redirect_target})
            return redirect(redirect_target)
        else:
            if is_ajax:
                return JsonResponse({"success": False, "errors": form.errors}, status=400)
            messages.error(request, "Invalid university email/registration number or password.")
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
def pending_approval_view(request):
    """
    Notice page shown to registered organizers while awaiting verification.
    """
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != RoleChoices.ORGANIZER:
        return redirect("accounts:dashboard_redirect")
    
    if profile.status == AccountStatus.ACTIVE:
        return redirect("organizer:dashboard")

    membership = ClubMembership.objects.filter(user=request.user).select_related("club").first()

    return render(request, "accounts/pending_approval.html", {
        "profile": profile,
        "membership": membership,
    })


def demo_login_organizer_view(request):
    """
    Instantly logs into the seeded Demo Organizer account.
    """
    user = User.objects.filter(username="demo_organizer").first()
    if user:
        login(request, user)
        messages.success(request, "Welcome! Logged in as Demo Organizer.")
    return redirect("public:home")


def demo_login_student_view(request):
    """
    Instantly logs into the seeded Demo Student account.
    """
    user = User.objects.filter(username="demo_student").first()
    if user:
        login(request, user)
        messages.success(request, "Welcome! Logged in as Demo Student.")
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
    elif profile and profile.role == RoleChoices.ORGANIZER:
        if profile.status == AccountStatus.ACTIVE:
            return redirect("organizer:dashboard")
        else:
            return redirect("accounts:pending_approval")
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

    membership = ClubMembership.objects.filter(user=request.user).select_related("club").first() if profile and profile.role == RoleChoices.ORGANIZER else None

    return render(request, "accounts/profile.html", {
        "form": form,
        "profile": profile,
        "membership": membership,
    })


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
