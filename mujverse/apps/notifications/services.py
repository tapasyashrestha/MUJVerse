"""
MUJVERSE — In-App Notifications Services & Email Dispatch
Handles creation of in-app notification records and environment-configured optional emails.
Never pretends an email was sent if no email backend/host is configured.
"""

import logging
from django.conf import settings
from django.core.mail import send_mail
from .models import Notification, NotificationType

logger = logging.getLogger(__name__)


def notify(
    recipient,
    title: str,
    message: str,
    notification_type: str = NotificationType.INFO,
    target_url: str = "",
    send_email: bool = False,
):
    """
    Creates an in-app notification record and optionally dispatches an email
    if EMAIL_HOST is properly configured in settings.
    """
    if not recipient:
        return None

    # 1. Create in-app notification
    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url or "",
    )

    # 2. Environment-configured optional email
    email_host = getattr(settings, "EMAIL_HOST", None)
    if send_email and email_host and recipient.email:
        try:
            from_email = getattr(
                settings, "DEFAULT_FROM_EMAIL", "noreply@muj.manipal.edu"
            )
            send_mail(
                subject=f"[MUJVERSE] {title}",
                message=f"Hello {recipient.username},\n\n{message}\n\nView details: {target_url}\n\n— The MUJVERSE Team",
                from_email=from_email,
                recipient_list=[recipient.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning("Optional email notification failed gracefully: %s", e)

    return notification
