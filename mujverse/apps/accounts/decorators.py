"""
Server-side authorization decorators for MUJVERSE.
Guarantees that access is validated on the backend.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from .models import RoleChoices


def role_required(*allowed_roles):
    """
    Decorator to restrict access to users having one of the specified roles.
    Superusers and staff always bypass.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.is_staff:
                return view_func(request, *args, **kwargs)

            profile = getattr(user, "profile", None)
            if profile and profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(
                request,
                "Access denied: You do not have permission to view this resource.",
            )
            raise PermissionDenied("You do not have the required role to access this page.")

        return _wrapped_view
    return decorator


def student_required(view_func):
    """Restrict view to authenticated students."""
    return role_required(RoleChoices.STUDENT)(view_func)


def organizer_required(view_func):
    """Restrict view to verified event organizers (or admins)."""
    return role_required(RoleChoices.ORGANIZER, RoleChoices.ADMIN)(view_func)


def admin_required(view_func):
    """Restrict view to administrators (platform admin or superusers)."""
    return role_required(RoleChoices.ADMIN)(view_func)
