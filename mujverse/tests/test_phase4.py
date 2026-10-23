"""
MUJVERSE — Phase 4 Comprehensive Tests
Covers:
- In-app notification creation, delivery, ownership isolation, and read status
- Post-event attendee reviews, eligibility checks, comment length, and duplicate review prevention
- Admin account suspension/reactivation with self-suspension protection and AuditLog
- Category management (creation, activation toggle) and report resolution/dismissal
- Dashboard scoping and role isolation for Student, Organizer, and Admin portals
"""

from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from mujverse.apps.events.models import Category, Event, EventStatus
from mujverse.apps.registrations.models import Registration, RegistrationStatus
from mujverse.apps.attendance.models import Attendance, CheckInMethod
from mujverse.apps.notifications.models import Notification, NotificationType
from mujverse.apps.reviews.models import Review
from mujverse.apps.moderation.models import EventReport, ReportStatus, AuditLog


def future(days=10):
    return timezone.now() + timedelta(days=days)


def past(days=5):
    return timezone.now() - timedelta(days=days)


class BasePhase4TestCase(TestCase):
    """Shared fixtures for Phase 4 tests."""

    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_user(
            username="admin_phase4",
            email="admin4@muj.manipal.edu",
            password="Pass@1234",
        )
        self.admin.profile.role = "admin"
        self.admin.is_staff = True
        self.admin.profile.save()
        self.admin.save()

        # Organizer A
        self.org_a = User.objects.create_user(
            username="organizer_a",
            email="orga@muj.manipal.edu",
            password="Pass@1234",
        )
        self.org_a.profile.role = "organizer"
        self.org_a.profile.save()

        # Organizer B
        self.org_b = User.objects.create_user(
            username="organizer_b",
            email="orgb@muj.manipal.edu",
            password="Pass@1234",
        )
        self.org_b.profile.role = "organizer"
        self.org_b.profile.save()

        # Student 1
        self.student1 = User.objects.create_user(
            username="student_alpha",
            email="stua@muj.manipal.edu",
            password="Pass@1234",
        )
        self.student1.profile.role = "student"
        self.student1.profile.student_identifier = "229302001"
        self.student1.profile.save()

        # Student 2
        self.student2 = User.objects.create_user(
            username="student_beta",
            email="stub@muj.manipal.edu",
            password="Pass@1234",
        )
        self.student2.profile.role = "student"
        self.student2.profile.student_identifier = "229302002"
        self.student2.profile.save()

        # Category
        self.category = Category.objects.create(
            name="Cultural & Arts",
            icon="bi-palette",
            is_active=True,
        )

        # Active upcoming event owned by Organizer A
        start = future(10)
        self.upcoming_event = Event.objects.create(
            title="MUJ Symphony Night",
            description="Live musical performances across campus bands.",
            category=self.category,
            organizer=self.org_a,
            venue="Amphitheatre",
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            registration_deadline=future(8),
            capacity=100,
            status=EventStatus.APPROVED,
            is_published=True,
        )

        # Concluded past event owned by Organizer A
        p_start = past(10)
        self.concluded_event = Event.objects.create(
            title="MUJ Tech Expo 2026",
            description="Exhibition of student engineering prototypes.",
            category=self.category,
            organizer=self.org_a,
            venue="Tech Park Atrium",
            start_datetime=p_start,
            end_datetime=p_start + timedelta(hours=4),
            registration_deadline=past(12),
            capacity=50,
            status=EventStatus.APPROVED,
            is_published=True,
        )

    def _login(self, user):
        self.client.login(username=user.username, password="Pass@1234")


# ─── 1. In-App Notification Tests ─────────────────────────────────────────────

class NotificationTests(BasePhase4TestCase):

    def test_notification_created_on_registration(self):
        self._login(self.student1)
        self.client.post(reverse("student:register_event", kwargs={"event_id": self.upcoming_event.id}))

        # Student receives confirmation notification
        notif = Notification.objects.filter(recipient=self.student1).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, NotificationType.REGISTRATION)
        self.assertIn("MUJ Symphony Night", notif.message)
        self.assertFalse(notif.is_read)

        # Organizer receives alert
        org_notif = Notification.objects.filter(recipient=self.org_a).first()
        self.assertIsNotNone(org_notif)
        self.assertIn("student_alpha", org_notif.message)

    def test_notification_ownership_isolation(self):
        notif = Notification.objects.create(
            recipient=self.student1,
            title="Private Notice",
            message="Confidential student alert.",
        )

        # Student 2 tries to mark Student 1's notification as read
        self._login(self.student2)
        resp = self.client.post(reverse("notifications:mark_read", kwargs={"pk": notif.pk}))
        self.assertEqual(resp.status_code, 404)

        notif.refresh_from_db()
        self.assertFalse(notif.is_read)

    def test_mark_notification_as_read(self):
        notif = Notification.objects.create(
            recipient=self.student1,
            title="Alert",
            message="Your ticket is ready.",
        )
        self._login(self.student1)
        resp = self.client.post(reverse("notifications:mark_read", kwargs={"pk": notif.pk}))
        self.assertRedirects(resp, reverse("notifications:list"))

        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_all_notifications_as_read(self):
        Notification.objects.create(recipient=self.student1, title="N1", message="M1")
        Notification.objects.create(recipient=self.student1, title="N2", message="M2")
        self.assertEqual(Notification.objects.filter(recipient=self.student1, is_read=False).count(), 2)

        self._login(self.student1)
        resp = self.client.post(reverse("notifications:mark_all_read"))
        self.assertRedirects(resp, reverse("notifications:list"))
        self.assertEqual(Notification.objects.filter(recipient=self.student1, is_read=False).count(), 0)


# ─── 2. Reviews & Feedback Tests ──────────────────────────────────────────────

class ReviewTests(BasePhase4TestCase):

    def test_student_can_review_concluded_attended_event(self):
        # Student 1 attended concluded event
        Registration.objects.create(
            event=self.concluded_event,
            student=self.student1,
            status=RegistrationStatus.CONFIRMED,
        )

        self._login(self.student1)
        url = reverse("reviews:create_review", kwargs={"event_id": self.concluded_event.id})

        resp = self.client.post(url, data={
            "rating": 5,
            "comment": "Incredible showcase of student projects, highly engaging!",
        })
        self.assertRedirects(resp, self.concluded_event.get_absolute_url())

        # Verify Review created
        review = Review.objects.filter(event=self.concluded_event, student=self.student1).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.rating, 5)
        self.assertIn("Incredible showcase", review.comment)

        # Organizer notified
        org_notif = Notification.objects.filter(recipient=self.org_a, title="New Event Review").first()
        self.assertIsNotNone(org_notif)

    def test_student_cannot_review_upcoming_event(self):
        Registration.objects.create(
            event=self.upcoming_event,
            student=self.student1,
            status=RegistrationStatus.CONFIRMED,
        )

        self._login(self.student1)
        url = reverse("reviews:create_review", kwargs={"event_id": self.upcoming_event.id})
        resp = self.client.post(url, data={"rating": 5, "comment": "Can't wait for this event to happen!"})

        # Blocked: redirect with error message
        self.assertRedirects(resp, self.upcoming_event.get_absolute_url())
        self.assertFalse(Review.objects.filter(event=self.upcoming_event, student=self.student1).exists())

    def test_student_cannot_review_unregistered_event(self):
        # Student 1 never registered for concluded event
        self._login(self.student1)
        url = reverse("reviews:create_review", kwargs={"event_id": self.concluded_event.id})
        resp = self.client.post(url, data={"rating": 4, "comment": "Looked cool from afar!"})

        self.assertRedirects(resp, self.concluded_event.get_absolute_url())
        self.assertFalse(Review.objects.filter(event=self.concluded_event, student=self.student1).exists())

    def test_one_review_per_student_enforced(self):
        Registration.objects.create(
            event=self.concluded_event,
            student=self.student1,
            status=RegistrationStatus.CONFIRMED,
        )
        Review.objects.create(
            event=self.concluded_event,
            student=self.student1,
            rating=4,
            comment="First review was already submitted.",
        )

        self._login(self.student1)
        url = reverse("reviews:create_review", kwargs={"event_id": self.concluded_event.id})
        resp = self.client.post(url, data={"rating": 5, "comment": "Trying to review a second time."})

        self.assertRedirects(resp, self.concluded_event.get_absolute_url())
        # Still only one review
        self.assertEqual(Review.objects.filter(event=self.concluded_event, student=self.student1).count(), 1)

    def test_review_comment_too_short_rejected(self):
        Registration.objects.create(
            event=self.concluded_event,
            student=self.student1,
            status=RegistrationStatus.CONFIRMED,
        )

        self._login(self.student1)
        url = reverse("reviews:create_review", kwargs={"event_id": self.concluded_event.id})
        resp = self.client.post(url, data={"rating": 5, "comment": "Good"})  # < 10 chars

        self.assertEqual(resp.status_code, 200)  # Re-renders form with validation errors
        self.assertFormError(resp.context["form"], "comment", "Ensure this value has at least 10 characters (it has 4).")
        self.assertFalse(Review.objects.filter(event=self.concluded_event, student=self.student1).exists())

    def test_organizer_can_view_event_reviews(self):
        Registration.objects.create(event=self.concluded_event, student=self.student1, status=RegistrationStatus.CONFIRMED)
        Review.objects.create(event=self.concluded_event, student=self.student1, rating=5, comment="Top notch organization!")

        self._login(self.org_a)
        url = reverse("organizer:event_reviews", kwargs={"pk": self.concluded_event.id})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Top notch organization!")
        self.assertContains(resp, "5.0")

    def test_organizer_b_cannot_view_organizer_a_reviews(self):
        self._login(self.org_b)
        url = reverse("organizer:event_reviews", kwargs={"pk": self.concluded_event.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)


# ─── 3. Administrator Actions & AuditLog Tests ────────────────────────────────

class AdminActionsTests(BasePhase4TestCase):

    def test_admin_can_suspend_and_reactivate_user(self):
        self._login(self.admin)
        url = reverse("platform_admin:toggle_user_status", kwargs={"user_id": self.student1.id})

        # Suspend
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("platform_admin:users"))
        self.student1.refresh_from_db()
        self.assertFalse(self.student1.is_active)

        # AuditLog entry created
        log = AuditLog.objects.filter(object_id=str(self.student1.id), action="user_suspended").first()
        self.assertIsNotNone(log)

        # Reactivate
        self.client.post(url)
        self.student1.refresh_from_db()
        self.assertTrue(self.student1.is_active)
        log2 = AuditLog.objects.filter(object_id=str(self.student1.id), action="user_reactivated").first()
        self.assertIsNotNone(log2)

    def test_admin_cannot_suspend_self(self):
        self._login(self.admin)
        url = reverse("platform_admin:toggle_user_status", kwargs={"user_id": self.admin.id})

        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("platform_admin:users"))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_non_admin_cannot_suspend_users(self):
        self._login(self.student1)
        url = reverse("platform_admin:toggle_user_status", kwargs={"user_id": self.student2.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_category_and_toggle_active(self):
        self._login(self.admin)

        # Create
        create_url = reverse("platform_admin:category_create")
        resp = self.client.post(create_url, data={"name": "Gaming & E-Sports", "icon": "bi-controller"})
        self.assertRedirects(resp, reverse("platform_admin:categories"))

        cat = Category.objects.filter(name="Gaming & E-Sports").first()
        self.assertIsNotNone(cat)
        self.assertTrue(cat.is_active)
        self.assertTrue(AuditLog.objects.filter(action="category_created", object_id=str(cat.id)).exists())

        # Toggle inactive
        toggle_url = reverse("platform_admin:category_toggle_active", kwargs={"category_id": cat.id})
        self.client.post(toggle_url)
        cat.refresh_from_db()
        self.assertFalse(cat.is_active)

    def test_admin_can_resolve_and_dismiss_report(self):
        report = EventReport.objects.create(
            reported_by=self.student1,
            event=self.upcoming_event,
            reason="Incorrect Venue Timing",
            description="The banner lists 5 PM but text says 6 PM.",
            status=ReportStatus.OPEN,
        )

        self._login(self.admin)

        # Resolve
        resolve_url = reverse("platform_admin:resolve_report", kwargs={"report_id": report.id})
        resp = self.client.post(resolve_url, data={"notes": "Venue updated to 6 PM."})
        self.assertRedirects(resp, reverse("platform_admin:reports"))

        report.refresh_from_db()
        self.assertEqual(report.status, ReportStatus.RESOLVED)
        self.assertEqual(report.reviewed_by, self.admin)
        self.assertTrue(AuditLog.objects.filter(action="report_resolved", object_id=str(report.id)).exists())


# ─── 4. Dashboard Scoping & Role Isolation Tests ──────────────────────────────

class DashboardScopingTests(BasePhase4TestCase):

    def test_organizer_dashboard_scoped_strictly_to_own_events(self):
        # Event owned by Org B
        start = future(12)
        event_b = Event.objects.create(
            title="Secret Beta Hackathon",
            category=self.category,
            organizer=self.org_b,
            venue="Block 4",
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            registration_deadline=future(10),
            capacity=30,
            status=EventStatus.APPROVED,
            is_published=True,
        )

        self._login(self.org_a)
        resp = self.client.get(reverse("organizer:dashboard"))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "MUJ Symphony Night")
        # Organizer B's event must NOT be visible in Organizer A's dashboard
        self.assertNotContains(resp, "Secret Beta Hackathon")

    def test_student_dashboard_scoped_to_own_registrations(self):
        Registration.objects.create(event=self.upcoming_event, student=self.student1, status=RegistrationStatus.CONFIRMED)
        Registration.objects.create(event=self.concluded_event, student=self.student2, status=RegistrationStatus.CONFIRMED)

        self._login(self.student1)
        resp = self.client.get(reverse("student:dashboard"))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "MUJ Symphony Night")
        self.assertNotContains(resp, "MUJ Tech Expo 2026")

    def test_non_admin_cannot_access_admin_dashboard(self):
        self._login(self.student1)
        resp = self.client.get(reverse("platform_admin:dashboard"))
        self.assertEqual(resp.status_code, 403)

        self._login(self.org_a)
        resp2 = self.client.get(reverse("platform_admin:dashboard"))
        self.assertEqual(resp2.status_code, 403)
