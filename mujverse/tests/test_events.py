"""
MUJVERSE — Phase 2 Event Management Tests
Covers: event creation, editing, validation, submission, approval, rejection,
cross-organizer access denial, and admin moderation with AuditLog.
"""

from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from mujverse.apps.events.models import Category, Event, EventStatus
from mujverse.apps.moderation.models import AuditLog


def future(days=10):
    """Return a timezone-aware datetime N days in the future."""
    return timezone.now() + timedelta(days=days)


def past(days=5):
    return timezone.now() - timedelta(days=days)


class BaseEventTestCase(TestCase):
    """Shared setUp: organizer, student, admin, category."""

    def setUp(self):
        self.client = Client()

        # Organizer A
        self.organizer = User.objects.create_user(
            username="org_alpha",
            email="org_alpha@muj.manipal.edu",
            password="Pass@1234",
        )
        self.organizer.profile.role = "organizer"
        self.organizer.profile.save()

        # Organizer B (attacker)
        self.organizer_b = User.objects.create_user(
            username="org_beta",
            email="org_beta@muj.manipal.edu",
            password="Pass@1234",
        )
        self.organizer_b.profile.role = "organizer"
        self.organizer_b.profile.save()

        # Student
        self.student = User.objects.create_user(
            username="stu_test",
            email="stu_test@muj.manipal.edu",
            password="Pass@1234",
        )
        self.student.profile.role = "student"
        self.student.profile.save()

        # Admin
        self.admin_user = User.objects.create_user(
            username="platform_admin",
            email="admin@muj.manipal.edu",
            password="Pass@1234",
        )
        self.admin_user.profile.role = "admin"
        self.admin_user.profile.save()

        # Category
        self.category = Category.objects.create(
            name="Technical",
            icon="bi-code-slash",
            is_active=True,
        )

    def _make_event(self, organizer=None, status=EventStatus.DRAFT, is_published=False):
        """Helper to quickly create a valid event."""
        start = future(15)
        return Event.objects.create(
            title="Test Event — Phase 2",
            description="A comprehensive test event for the MUJVERSE platform.",
            category=self.category,
            organizer=organizer or self.organizer,
            venue="Test Hall 1",
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            registration_deadline=future(10),
            capacity=100,
            status=status,
            is_published=is_published,
        )

    def _login(self, user):
        self.client.force_login(user)


# ─── Organizer: Create ────────────────────────────────────────

class EventCreateTests(BaseEventTestCase):

    def test_organizer_can_access_create_form(self):
        self._login(self.organizer)
        resp = self.client.get(reverse("organizer:event_create"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Create Event")

    def test_student_cannot_access_create_form(self):
        self._login(self.student)
        resp = self.client.get(reverse("organizer:event_create"))
        self.assertNotEqual(resp.status_code, 200)

    def test_anonymous_redirected_from_create(self):
        resp = self.client.get(reverse("organizer:event_create"))
        self.assertEqual(resp.status_code, 302)

    def test_valid_form_creates_draft(self):
        self._login(self.organizer)
        start = future(15)
        data = {
            "title": "New Draft Event",
            "category": self.category.pk,
            "description": "A long enough description for the form to accept it without error.",
            "venue": "Room 101",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": (start + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M"),
            "registration_deadline": future(10).strftime("%Y-%m-%dT%H:%M"),
            "capacity": 50,
            "action": "save",
        }
        resp = self.client.post(reverse("organizer:event_create"), data)
        self.assertEqual(resp.status_code, 302)
        event = Event.objects.get(title="New Draft Event")
        self.assertEqual(event.status, EventStatus.DRAFT)
        self.assertEqual(event.organizer, self.organizer)

    def test_title_too_short_raises_error(self):
        self._login(self.organizer)
        start = future(15)
        data = {
            "title": "Hi",  # Only 2 characters
            "category": self.category.pk,
            "description": "A long enough description for the form to accept it.",
            "venue": "Room 101",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": (start + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M"),
            "registration_deadline": future(10).strftime("%Y-%m-%dT%H:%M"),
            "capacity": 50,
            "action": "save",
        }
        resp = self.client.post(reverse("organizer:event_create"), data)
        self.assertEqual(resp.status_code, 200)  # Re-renders form with errors
        self.assertFalse(Event.objects.filter(title="Hi").exists())

    def test_end_before_start_fails(self):
        self._login(self.organizer)
        start = future(15)
        data = {
            "title": "Invalid Schedule",
            "category": self.category.pk,
            "description": "A valid long description with enough content to pass form validation.",
            "venue": "Room 102",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": (start - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),  # BEFORE start
            "registration_deadline": future(10).strftime("%Y-%m-%dT%H:%M"),
            "capacity": 50,
            "action": "save",
        }
        resp = self.client.post(reverse("organizer:event_create"), data)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Invalid Schedule").exists())

    def test_deadline_after_start_fails(self):
        self._login(self.organizer)
        start = future(15)
        data = {
            "title": "Bad Deadline Event",
            "category": self.category.pk,
            "description": "A valid long description with enough content to pass form validation.",
            "venue": "Hall A",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": (start + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M"),
            "registration_deadline": future(20).strftime("%Y-%m-%dT%H:%M"),  # AFTER start
            "capacity": 50,
            "action": "save",
        }
        resp = self.client.post(reverse("organizer:event_create"), data)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Bad Deadline Event").exists())

    def test_create_and_submit_sets_pending_status(self):
        self._login(self.organizer)
        start = future(15)
        data = {
            "title": "Submit On Create",
            "category": self.category.pk,
            "description": "A valid long description with enough content to pass form validation.",
            "venue": "Auditorium",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": (start + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"),
            "registration_deadline": future(10).strftime("%Y-%m-%dT%H:%M"),
            "capacity": 200,
            "action": "submit",  # Submit directly
        }
        resp = self.client.post(reverse("organizer:event_create"), data)
        self.assertEqual(resp.status_code, 302)
        event = Event.objects.get(title="Submit On Create")
        self.assertEqual(event.status, EventStatus.PENDING_APPROVAL)


# ─── Organizer: Edit ──────────────────────────────────────────

class EventEditTests(BaseEventTestCase):

    def test_organizer_can_edit_own_draft(self):
        event = self._make_event(status=EventStatus.DRAFT)
        self._login(self.organizer)
        resp = self.client.get(reverse("organizer:event_edit", kwargs={"pk": event.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_organizer_b_cannot_edit_organizer_a_event(self):
        """Cross-organizer access must be denied at the server level."""
        event = self._make_event(organizer=self.organizer, status=EventStatus.DRAFT)
        self._login(self.organizer_b)
        resp = self.client.get(reverse("organizer:event_edit", kwargs={"pk": event.pk}))
        self.assertIn(resp.status_code, [302, 403])

    def test_cannot_edit_approved_event(self):
        event = self._make_event(status=EventStatus.APPROVED, is_published=True)
        self._login(self.organizer)
        resp = self.client.get(reverse("organizer:event_edit", kwargs={"pk": event.pk}))
        self.assertEqual(resp.status_code, 302)

    def test_can_edit_rejected_event(self):
        event = self._make_event(status=EventStatus.REJECTED)
        self._login(self.organizer)
        resp = self.client.get(reverse("organizer:event_edit", kwargs={"pk": event.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_editing_rejected_clears_rejection_reason(self):
        event = self._make_event(status=EventStatus.REJECTED)
        event.rejection_reason = "Cover image missing."
        event.save()
        self._login(self.organizer)
        start = future(15)
        data = {
            "title": "Resubmitted Event Fix",
            "category": self.category.pk,
            "description": "Fixed description with sufficient length to satisfy validation rules.",
            "venue": "Hall B",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": (start + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "registration_deadline": future(10).strftime("%Y-%m-%dT%H:%M"),
            "capacity": 80,
            "action": "save",
        }
        self.client.post(reverse("organizer:event_edit", kwargs={"pk": event.pk}), data)
        event.refresh_from_db()
        self.assertEqual(event.rejection_reason, "")


# ─── Organizer: Submit & Delete ───────────────────────────────

class EventSubmitDeleteTests(BaseEventTestCase):

    def test_submit_changes_status_to_pending(self):
        event = self._make_event(status=EventStatus.DRAFT)
        self._login(self.organizer)
        resp = self.client.post(reverse("organizer:event_submit", kwargs={"pk": event.pk}))
        self.assertEqual(resp.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.PENDING_APPROVAL)

    def test_organizer_b_cannot_submit_organizer_a_event(self):
        event = self._make_event(organizer=self.organizer, status=EventStatus.DRAFT)
        self._login(self.organizer_b)
        resp = self.client.post(reverse("organizer:event_submit", kwargs={"pk": event.pk}))
        self.assertIn(resp.status_code, [302, 403, 404])
        event.refresh_from_db()
        # Status must NOT have changed
        self.assertEqual(event.status, EventStatus.DRAFT)

    def test_approved_event_cannot_be_submitted(self):
        event = self._make_event(status=EventStatus.APPROVED, is_published=True)
        self._login(self.organizer)
        self.client.post(reverse("organizer:event_submit", kwargs={"pk": event.pk}))
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.APPROVED)

    def test_organizer_can_delete_own_draft(self):
        event = self._make_event(status=EventStatus.DRAFT)
        self._login(self.organizer)
        pk = event.pk
        self.client.post(reverse("organizer:event_delete", kwargs={"pk": pk}))
        self.assertFalse(Event.objects.filter(pk=pk).exists())

    def test_organizer_cannot_delete_approved_event(self):
        event = self._make_event(status=EventStatus.APPROVED, is_published=True)
        self._login(self.organizer)
        pk = event.pk
        self.client.post(reverse("organizer:event_delete", kwargs={"pk": pk}))
        # Must still exist
        self.assertTrue(Event.objects.filter(pk=pk).exists())


# ─── Administrator: Approval & Rejection ─────────────────────

class AdminModerationTests(BaseEventTestCase):

    def test_admin_can_access_pending_queue(self):
        self._login(self.admin_user)
        resp = self.client.get(reverse("platform_admin:pending_events"))
        self.assertEqual(resp.status_code, 200)

    def test_non_admin_cannot_access_pending_queue(self):
        self._login(self.organizer)
        resp = self.client.get(reverse("platform_admin:pending_events"))
        self.assertNotEqual(resp.status_code, 200)

    def test_approve_event_sets_approved_and_published(self):
        event = self._make_event(status=EventStatus.PENDING_APPROVAL)
        self._login(self.admin_user)
        resp = self.client.post(reverse("platform_admin:approve_event", kwargs={"pk": event.pk}))
        self.assertEqual(resp.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.APPROVED)
        self.assertTrue(event.is_published)

    def test_approve_writes_auditlog(self):
        event = self._make_event(status=EventStatus.PENDING_APPROVAL)
        self._login(self.admin_user)
        before = AuditLog.objects.count()
        self.client.post(reverse("platform_admin:approve_event", kwargs={"pk": event.pk}))
        self.assertEqual(AuditLog.objects.count(), before + 1)
        log = AuditLog.objects.latest("created_at")
        self.assertEqual(log.action, "event_approved")
        self.assertEqual(log.actor, self.admin_user)

    def test_reject_event_requires_reason(self):
        event = self._make_event(status=EventStatus.PENDING_APPROVAL)
        self._login(self.admin_user)
        resp = self.client.post(
            reverse("platform_admin:reject_event", kwargs={"pk": event.pk}),
            {"rejection_reason": ""},  # Empty reason
        )
        self.assertEqual(resp.status_code, 200)  # Re-renders form
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.PENDING_APPROVAL)

    def test_reject_event_with_reason_sets_rejected(self):
        event = self._make_event(status=EventStatus.PENDING_APPROVAL)
        self._login(self.admin_user)
        resp = self.client.post(
            reverse("platform_admin:reject_event", kwargs={"pk": event.pk}),
            {"rejection_reason": "Cover image is inappropriate and must be replaced."},
        )
        self.assertEqual(resp.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.REJECTED)
        self.assertFalse(event.is_published)
        self.assertIn("inappropriate", event.rejection_reason)

    def test_reject_writes_auditlog(self):
        event = self._make_event(status=EventStatus.PENDING_APPROVAL)
        self._login(self.admin_user)
        before = AuditLog.objects.count()
        self.client.post(
            reverse("platform_admin:reject_event", kwargs={"pk": event.pk}),
            {"rejection_reason": "Missing required information about the speaker and schedule."},
        )
        self.assertEqual(AuditLog.objects.count(), before + 1)
        log = AuditLog.objects.latest("created_at")
        self.assertEqual(log.action, "event_rejected")

    def test_cannot_approve_non_pending_event(self):
        event = self._make_event(status=EventStatus.DRAFT)
        self._login(self.admin_user)
        self.client.post(reverse("platform_admin:approve_event", kwargs={"pk": event.pk}))
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.DRAFT)

    def test_student_cannot_approve(self):
        event = self._make_event(status=EventStatus.PENDING_APPROVAL)
        self._login(self.student)
        resp = self.client.post(reverse("platform_admin:approve_event", kwargs={"pk": event.pk}))
        self.assertNotEqual(resp.status_code, 200)
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.PENDING_APPROVAL)


# ─── Full Resubmission Workflow ───────────────────────────────

class ResubmissionWorkflowTests(BaseEventTestCase):
    """
    Full lifecycle: draft → submit → reject → re-edit → resubmit → approve
    """

    def test_full_resubmission_cycle(self):
        # 1. Organizer creates a draft
        event = self._make_event(status=EventStatus.DRAFT)
        self.assertEqual(event.status, EventStatus.DRAFT)

        # 2. Organizer submits for approval
        self._login(self.organizer)
        self.client.post(reverse("organizer:event_submit", kwargs={"pk": event.pk}))
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.PENDING_APPROVAL)

        # 3. Admin rejects with a reason
        self._login(self.admin_user)
        self.client.post(
            reverse("platform_admin:reject_event", kwargs={"pk": event.pk}),
            {"rejection_reason": "Please add a more detailed description of the schedule."},
        )
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.REJECTED)

        # 4. Organizer re-edits the rejected event
        self._login(self.organizer)
        start = future(15)
        data = {
            "title": "Test Event — Phase 2 (Revised)",
            "category": self.category.pk,
            "description": "Updated and comprehensive description with full schedule, speakers, and requirements for attendees.",
            "venue": "Test Hall 1",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": (start + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M"),
            "registration_deadline": future(10).strftime("%Y-%m-%dT%H:%M"),
            "capacity": 100,
            "action": "save",
        }
        self.client.post(reverse("organizer:event_edit", kwargs={"pk": event.pk}), data)
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.REJECTED)  # Still rejected until resubmitted
        self.assertEqual(event.rejection_reason, "")  # Reason cleared

        # 5. Organizer resubmits
        self.client.post(reverse("organizer:event_submit", kwargs={"pk": event.pk}))
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.PENDING_APPROVAL)

        # 6. Admin approves
        self._login(self.admin_user)
        self.client.post(reverse("platform_admin:approve_event", kwargs={"pk": event.pk}))
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.APPROVED)
        self.assertTrue(event.is_published)

        # 7. Verify 2 AuditLog entries
        logs = AuditLog.objects.filter(object_id=str(event.pk)).order_by("created_at")
        self.assertEqual(logs.count(), 2)
        self.assertEqual(logs[0].action, "event_rejected")
        self.assertEqual(logs[1].action, "event_approved")


# ─── Public Visibility ────────────────────────────────────────

class PublicVisibilityTests(BaseEventTestCase):

    def test_draft_event_not_visible_to_public(self):
        event = self._make_event(status=EventStatus.DRAFT)
        resp = self.client.get(reverse("public:event_detail", kwargs={"slug": event.slug}))
        self.assertEqual(resp.status_code, 302)  # Redirected away

    def test_approved_published_event_visible_to_public(self):
        event = self._make_event(status=EventStatus.APPROVED, is_published=True)
        resp = self.client.get(reverse("public:event_detail", kwargs={"slug": event.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, event.title)

    def test_owner_can_preview_own_draft(self):
        event = self._make_event(status=EventStatus.DRAFT)
        self._login(self.organizer)
        resp = self.client.get(reverse("public:event_detail", kwargs={"slug": event.slug}))
        self.assertEqual(resp.status_code, 200)

    def test_explore_shows_only_public_events(self):
        # Create one draft, one approved+published
        self._make_event(status=EventStatus.DRAFT)
        approved = self._make_event(status=EventStatus.APPROVED, is_published=True)
        # Update title to differentiate
        approved.title = "Approved Public Event"
        approved.slug = ""
        approved.save()

        resp = self.client.get(reverse("public:explore"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Approved Public Event")
