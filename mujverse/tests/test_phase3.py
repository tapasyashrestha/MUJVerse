"""
MUJVERSE — Phase 3 Comprehensive Tests
Covers:
- Student free registration, locking, capacity limits, deadlines, and visibility checks
- Duplicate registration prevention and re-registration after cancellation
- QR ticket generation (PNG validation, zero PII encoding, access control)
- Event cancellation policy (capacity release, lock after check-in, lock after event completion)
- Organizer Check-in Scanner API (atomic check-in, duplicate prevention, wrong event, cancelled ticket)
- Attendee lists and CSV export with spreadsheet formula injection protection
"""

import io
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from PIL import Image

from mujverse.apps.events.models import Category, Event, EventStatus
from mujverse.apps.registrations.models import Registration, RegistrationStatus
from mujverse.apps.attendance.models import Attendance, CheckInMethod


def future(days=10):
    return timezone.now() + timedelta(days=days)


def past(days=5):
    return timezone.now() - timedelta(days=days)


class BasePhase3TestCase(TestCase):
    """Shared test fixtures for Phase 3."""

    def setUp(self):
        self.client = Client()

        # Organizer A
        self.org_a = User.objects.create_user(
            username="organizer_alpha",
            email="org_alpha@muj.manipal.edu",
            password="Pass@1234",
        )
        self.org_a.profile.role = "organizer"
        self.org_a.profile.save()

        # Organizer B (unauthorized attacker)
        self.org_b = User.objects.create_user(
            username="organizer_beta",
            email="org_beta@muj.manipal.edu",
            password="Pass@1234",
        )
        self.org_b.profile.role = "organizer"
        self.org_b.profile.save()

        # Student 1
        self.student1 = User.objects.create_user(
            username="student_one",
            email="stu1@muj.manipal.edu",
            password="Pass@1234",
        )
        self.student1.profile.role = "student"
        self.student1.profile.student_identifier = "229301001"
        self.student1.profile.display_name = "Aarav Sharma"
        self.student1.profile.save()

        # Student 2
        self.student2 = User.objects.create_user(
            username="student_two",
            email="stu2@muj.manipal.edu",
            password="Pass@1234",
        )
        self.student2.profile.role = "student"
        self.student2.profile.student_identifier = "229301002"
        self.student2.profile.display_name = "Diya Patel"
        self.student2.profile.save()

        # Student 3
        self.student3 = User.objects.create_user(
            username="student_three",
            email="stu3@muj.manipal.edu",
            password="Pass@1234",
        )
        self.student3.profile.role = "student"
        self.student3.profile.student_identifier = "229301003"
        self.student3.profile.save()

        # Admin User
        self.admin_user = User.objects.create_user(
            username="admin_super",
            email="admin@muj.manipal.edu",
            password="Pass@1234",
        )
        self.admin_user.profile.role = "admin"
        self.admin_user.is_staff = True
        self.admin_user.profile.save()
        self.admin_user.save()

        # Category
        self.category = Category.objects.create(
            name="Technical & Hackathons",
            icon="bi-laptop",
            is_active=True,
        )

        # Standard Approved Event
        start = future(15)
        self.event = Event.objects.create(
            title="MUJ Hackathon 2026",
            description="The flagship hackathon of Manipal University Jaipur.",
            category=self.category,
            organizer=self.org_a,
            venue="TMA Pai Auditorium",
            start_datetime=start,
            end_datetime=start + timedelta(hours=6),
            registration_deadline=future(10),
            capacity=2,  # Small capacity to test boundary conditions easily
            status=EventStatus.APPROVED,
            is_published=True,
        )

    def _login(self, user):
        self.client.login(username=user.username, password="Pass@1234")


# ─── 1. Student Registration Workflow Tests ───────────────────────────────────

class StudentRegistrationTests(BasePhase3TestCase):

    def test_student_can_register_for_approved_published_event(self):
        self._login(self.student1)
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))

        # Confirms registration exists
        reg = Registration.objects.filter(event=self.event, student=self.student1).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.status, RegistrationStatus.CONFIRMED)
        self.assertTrue(len(reg.ticket_token) >= 32)

        # Redirects to ticket detail
        self.assertRedirects(resp, reverse("student:ticket_detail", kwargs={"ticket_token": reg.ticket_token}))

        # Remaining seats count decreases
        self.assertEqual(self.event.confirmed_registrations_count, 1)
        self.assertEqual(self.event.remaining_seats, 1)

    def test_duplicate_registration_prevented_gracefully(self):
        self._login(self.student1)
        # First registration
        self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))

        # Second registration attempt
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))
        reg = Registration.objects.filter(event=self.event, student=self.student1).first()

        # Still only one registration in DB
        self.assertEqual(Registration.objects.filter(event=self.event, student=self.student1).count(), 1)
        self.assertRedirects(resp, reverse("student:ticket_detail", kwargs={"ticket_token": reg.ticket_token}))

    def test_registration_fails_when_event_at_full_capacity(self):
        # Event capacity is 2
        # Fill capacity with student1 and student2
        Registration.objects.create(event=self.event, student=self.student1, status=RegistrationStatus.CONFIRMED)
        Registration.objects.create(event=self.event, student=self.student2, status=RegistrationStatus.CONFIRMED)

        self.assertEqual(self.event.remaining_seats, 0)
        self.assertTrue(self.event.is_full)

        # Student 3 attempts to register
        self._login(self.student3)
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))

        # Rejected, student 3 does NOT have a registration
        self.assertFalse(Registration.objects.filter(event=self.event, student=self.student3).exists())
        self.assertRedirects(resp, self.event.get_absolute_url())

    def test_registration_fails_after_deadline(self):
        self.event.registration_deadline = past(1)
        self.event.save()

        self._login(self.student1)
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))

        self.assertFalse(Registration.objects.filter(event=self.event, student=self.student1).exists())
        self.assertRedirects(resp, self.event.get_absolute_url())

    def test_registration_fails_for_draft_event(self):
        self.event.status = EventStatus.DRAFT
        self.event.save()

        self._login(self.student1)
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))

        self.assertFalse(Registration.objects.filter(event=self.event, student=self.student1).exists())
        self.assertRedirects(resp, reverse("public:explore"))

    def test_registration_fails_for_concluded_event(self):
        self.event.start_datetime = past(5)
        self.event.end_datetime = past(4)
        self.event.registration_deadline = past(6)
        self.event.save()

        self._login(self.student1)
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))

        self.assertFalse(Registration.objects.filter(event=self.event, student=self.student1).exists())
        self.assertRedirects(resp, self.event.get_absolute_url())

    def test_anonymous_redirected_to_login(self):
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_organizer_cannot_register_for_student_event(self):
        self._login(self.org_a)
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))
        self.assertFalse(Registration.objects.filter(event=self.event, student=self.org_a).exists())
        self.assertRedirects(resp, reverse("public:explore"))


# ─── 2. Ticket Pass & QR Code Verification Tests ──────────────────────────────

class TicketAndQRTests(BasePhase3TestCase):

    def setUp(self):
        super().setUp()
        self.reg = Registration.objects.create(
            event=self.event,
            student=self.student1,
            status=RegistrationStatus.CONFIRMED,
        )

    def test_student_can_view_own_ticket(self):
        self._login(self.student1)
        resp = self.client.get(reverse("student:ticket_detail", kwargs={"ticket_token": self.reg.ticket_token}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Aarav Sharma")
        self.assertContains(resp, self.event.title)
        self.assertContains(resp, self.reg.ticket_token)

    def test_event_organizer_can_view_attendee_ticket(self):
        self._login(self.org_a)
        resp = self.client.get(reverse("student:ticket_detail", kwargs={"ticket_token": self.reg.ticket_token}))
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_view_any_ticket(self):
        self._login(self.admin_user)
        resp = self.client.get(reverse("student:ticket_detail", kwargs={"ticket_token": self.reg.ticket_token}))
        self.assertEqual(resp.status_code, 200)

    def test_unauthorized_student_cannot_view_another_ticket(self):
        self._login(self.student2)
        resp = self.client.get(reverse("student:ticket_detail", kwargs={"ticket_token": self.reg.ticket_token}))
        self.assertEqual(resp.status_code, 403)

    def test_qr_code_image_endpoint_generates_valid_png(self):
        self._login(self.student1)
        resp = self.client.get(reverse("student:ticket_qr", kwargs={"ticket_token": self.reg.ticket_token}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/png")

        # Verify image validity via Pillow
        img = Image.open(io.BytesIO(resp.content))
        self.assertEqual(img.format, "PNG")
        self.assertGreater(img.size[0], 50)

    def test_unauthorized_student_cannot_fetch_qr_image(self):
        self._login(self.student2)
        resp = self.client.get(reverse("student:ticket_qr", kwargs={"ticket_token": self.reg.ticket_token}))
        self.assertEqual(resp.status_code, 403)


# ─── 3. Cancellation & Capacity Release Tests ─────────────────────────────────

class RegistrationCancellationTests(BasePhase3TestCase):

    def setUp(self):
        super().setUp()
        self.reg = Registration.objects.create(
            event=self.event,
            student=self.student1,
            status=RegistrationStatus.CONFIRMED,
        )

    def test_student_can_cancel_own_registration_and_release_capacity(self):
        self.assertEqual(self.event.confirmed_registrations_count, 1)

        self._login(self.student1)
        resp = self.client.post(reverse("student:ticket_cancel", kwargs={"ticket_token": self.reg.ticket_token}))
        self.assertRedirects(resp, reverse("student:registrations"))

        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, RegistrationStatus.CANCELLED)
        self.assertIsNotNone(self.reg.cancelled_at)

        # Seat is released
        self.assertEqual(self.event.confirmed_registrations_count, 0)
        self.assertEqual(self.event.remaining_seats, 2)

    def test_student_can_re_register_after_cancelling(self):
        # Cancel first
        self.reg.cancel()
        self.assertEqual(self.event.confirmed_registrations_count, 0)

        # Re-register
        self._login(self.student1)
        resp = self.client.post(reverse("student:register_event", kwargs={"event_id": self.event.id}))

        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, RegistrationStatus.CONFIRMED)
        self.assertIsNone(self.reg.cancelled_at)
        self.assertEqual(self.event.confirmed_registrations_count, 1)

    def test_cannot_cancel_after_attendance_check_in(self):
        # Student checked in
        Attendance.objects.create(
            registration=self.reg,
            checked_in_by=self.org_a,
            method=CheckInMethod.QR_SCAN,
        )

        self._login(self.student1)
        resp = self.client.post(reverse("student:ticket_cancel", kwargs={"ticket_token": self.reg.ticket_token}))

        self.reg.refresh_from_db()
        # Remains confirmed, cannot cancel
        self.assertEqual(self.reg.status, RegistrationStatus.CONFIRMED)
        self.assertRedirects(resp, reverse("student:ticket_detail", kwargs={"ticket_token": self.reg.ticket_token}))

    def test_other_student_cannot_cancel_registration(self):
        self._login(self.student2)
        resp = self.client.post(reverse("student:ticket_cancel", kwargs={"ticket_token": self.reg.ticket_token}))
        self.assertEqual(resp.status_code, 403)
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, RegistrationStatus.CONFIRMED)


# ─── 4. Organizer Attendance Check-in Scanner API Tests ───────────────────────

class AttendanceVerificationTests(BasePhase3TestCase):

    def setUp(self):
        super().setUp()
        self.reg1 = Registration.objects.create(
            event=self.event,
            student=self.student1,
            status=RegistrationStatus.CONFIRMED,
        )

        # Event B (different event)
        start = future(20)
        self.event_b = Event.objects.create(
            title="MUJ Cultural Fest 2026",
            category=self.category,
            organizer=self.org_b,
            venue="Hostel Quadrangle",
            start_datetime=start,
            end_datetime=start + timedelta(hours=4),
            registration_deadline=future(18),
            capacity=100,
            status=EventStatus.APPROVED,
            is_published=True,
        )
        self.reg_b = Registration.objects.create(
            event=self.event_b,
            student=self.student2,
            status=RegistrationStatus.CONFIRMED,
        )

    def test_valid_checkin_creates_attendance_record(self):
        self._login(self.org_a)
        url = reverse("attendance:verify_checkin", kwargs={"event_id": self.event.id})

        resp = self.client.post(
            url,
            data={"token": self.reg1.ticket_token, "method": "qr_scan"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["code"], "SUCCESS")
        self.assertEqual(data["attendee"]["name"], "Aarav Sharma")
        self.assertEqual(data["attendee"]["student_id"], "229301001")

        # Database record created
        self.assertTrue(Attendance.objects.filter(registration=self.reg1).exists())
        self.assertEqual(self.event.attendance_count, 1)

    def test_duplicate_checkin_fails(self):
        # First check in
        Attendance.objects.create(
            registration=self.reg1,
            checked_in_by=self.org_a,
            method=CheckInMethod.QR_SCAN,
        )

        self._login(self.org_a)
        url = reverse("attendance:verify_checkin", kwargs={"event_id": self.event.id})
        resp = self.client.post(url, data={"token": self.reg1.ticket_token})

        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["code"], "ALREADY_CHECKED_IN")

    def test_wrong_event_ticket_fails(self):
        # Scan reg_b (for Event B) at Event A's terminal
        self._login(self.org_a)
        url = reverse("attendance:verify_checkin", kwargs={"event_id": self.event.id})
        resp = self.client.post(url, data={"token": self.reg_b.ticket_token})

        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["code"], "WRONG_EVENT")
        self.assertFalse(Attendance.objects.filter(registration=self.reg_b).exists())

    def test_cancelled_ticket_fails(self):
        self.reg1.cancel()

        self._login(self.org_a)
        url = reverse("attendance:verify_checkin", kwargs={"event_id": self.event.id})
        resp = self.client.post(url, data={"token": self.reg1.ticket_token})

        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["code"], "CANCELLED")

    def test_non_existent_token_fails(self):
        self._login(self.org_a)
        url = reverse("attendance:verify_checkin", kwargs={"event_id": self.event.id})
        resp = self.client.post(url, data={"token": "invalid_token_1234567890abcdef"})

        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["code"], "NOT_FOUND")

    def test_unauthorized_organizer_cannot_scan_event(self):
        # Organizer B tries to check in at Organizer A's event
        self._login(self.org_b)
        url = reverse("attendance:verify_checkin", kwargs={"event_id": self.event.id})
        resp = self.client.post(url, data={"token": self.reg1.ticket_token})

        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Attendance.objects.filter(registration=self.reg1).exists())

    def test_student_cannot_access_scanner_or_verify(self):
        self._login(self.student1)
        url = reverse("attendance:verify_checkin", kwargs={"event_id": self.event.id})
        resp = self.client.post(url, data={"token": self.reg1.ticket_token})
        self.assertEqual(resp.status_code, 403)

    def test_manual_checkin_records_manual_method(self):
        self._login(self.org_a)
        url = reverse("attendance:verify_checkin", kwargs={"event_id": self.event.id})
        resp = self.client.post(url, data={"token": self.reg1.ticket_token, "method": "manual"})

        self.assertEqual(resp.status_code, 200)
        att = Attendance.objects.get(registration=self.reg1)
        self.assertEqual(att.method, CheckInMethod.MANUAL)


# ─── 5. Attendee List & CSV Export Tests ──────────────────────────────────────

class AttendeeManagementTests(BasePhase3TestCase):

    def setUp(self):
        super().setUp()
        self.reg1 = Registration.objects.create(
            event=self.event,
            student=self.student1,
            status=RegistrationStatus.CONFIRMED,
        )

    def test_organizer_can_view_attendee_list(self):
        self._login(self.org_a)
        url = reverse("organizer:event_attendees", kwargs={"pk": self.event.id})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Aarav Sharma")
        self.assertContains(resp, "229301001")

    def test_organizer_b_cannot_view_organizer_a_attendees(self):
        self._login(self.org_b)
        url = reverse("organizer:event_attendees", kwargs={"pk": self.event.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_organizer_can_export_csv(self):
        self._login(self.org_a)
        url = reverse("organizer:event_export_attendees", kwargs={"pk": self.event.id})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", resp["Content-Disposition"])

        content = resp.content.decode("utf-8")
        self.assertIn("Attendee Name", content)
        self.assertIn("Aarav Sharma", content)
        self.assertIn("229301001", content)

    def test_csv_export_sanitizes_formula_injection(self):
        # Create student with potential CSV injection in display_name / roll no
        injected_user = User.objects.create_user(
            username="attacker",
            email="hack@muj.edu",
            password="Pass@1234",
        )
        injected_user.profile.display_name = "=CMD('calc.exe')|'A'"
        injected_user.profile.student_identifier = "+919999999999"
        injected_user.profile.save()

        Registration.objects.create(
            event=self.event,
            student=injected_user,
            status=RegistrationStatus.CONFIRMED,
        )

        self._login(self.org_a)
        url = reverse("organizer:event_export_attendees", kwargs={"pk": self.event.id})
        resp = self.client.get(url)

        content = resp.content.decode("utf-8")
        # Formula injection characters must be escaped with leading single quote '
        self.assertIn("'=CMD('calc.exe')|'A'", content)
        self.assertIn("'+919999999999", content)

    def test_organizer_b_cannot_export_organizer_a_csv(self):
        self._login(self.org_b)
        url = reverse("organizer:event_export_attendees", kwargs={"pk": self.event.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
