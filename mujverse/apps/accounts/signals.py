"""
Signal handlers for automatic Profile lifecycle management.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, RoleChoices


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """
    Ensure every created User has an associated Profile.
    New users default to the least-privileged STUDENT role.
    Superusers automatically receive ADMIN role.
    """
    if created:
        role = RoleChoices.ADMIN if instance.is_superuser else RoleChoices.STUDENT
        display = instance.get_full_name() or instance.username
        Profile.objects.create(
            user=instance,
            role=role,
            display_name=display,
        )
    else:
        # Save profile if it exists, otherwise create it defensively
        if hasattr(instance, "profile"):
            instance.profile.save()
        else:
            role = RoleChoices.ADMIN if instance.is_superuser else RoleChoices.STUDENT
            Profile.objects.create(
                user=instance,
                role=role,
                display_name=instance.get_full_name() or instance.username,
            )
