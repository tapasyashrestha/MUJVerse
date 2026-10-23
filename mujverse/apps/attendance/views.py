"""
MUJVERSE — Attendance Views & Scanner Endpoint
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from mujverse.apps.accounts.decorators import organizer_required
from mujverse.apps.events.models import Event


@organizer_required
def scanner_view(request, event_id):
    """
    QR code scanner page for an authorized organizer.
    """
    event = get_object_or_404(Event, id=event_id)
    # Check that organizer owns this event or is admin
    if event.organizer_id != request.user.id and not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You can only scan tickets for your own events.")

    return render(request, "organizer/scanner.html", {"event": event})
