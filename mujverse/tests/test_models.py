"""
MUJVERSE — Core Domain Models Unit Tests
Validates relationships, database constraints, business validations, and querysets.
"""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from mujverse.apps.events.models import Category, Event, EventStatus
from mujverse.apps.registrations.models import Registration, RegistrationStatus
from mujverse.apps.attendance.models import Attendance, CheckInMethod
from mujverse.apps.reviews.models import Review
from mujverse.apps.notifications.models import Notification
from mujverse.apps.moderation.models import AuditLog


class ModelIntegrityTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="org_dev",
            email="org@muj.manipal.edu",
            password="Password123!",
        )
        self.organizer.profile.role = "organizer"
        self.organizer.profile.save()

        self.student = User.objects.create_user(
            username="student_vikram",
            email="vikram@muj.manipal.edu",
            password="Password123!",
        )

        self.category = Category.objects.create(
            name="Technical & Hackathons",
            description="Coding and hackathon events",
        )

    def test_category_auto_slug(self):
        self.assertEqual(self.category.slug, "technical-hackathons")

    def test_event_valid_creation(self):
        start = timezone.now() + timedelta(days=5)
        end = start + timedelta(hours=3)
        deadline = start - timedelta(hours=6)

        event = Event.objects.create(
            title="MUJ Hackathon 2026",
            category=self.category,
            organizer=self.organizer,
            venue="Grand Hall 1",
            start_datetime=start,
            end_datetime=end,
            registration_deadline=deadline,
            capacity=100,
            status=EventStatus.APPROVED,
            is_published=True,
        )
        self.assertTrue(event.slug.startswith("muj-hackathon-2026"))
        self.assertTrue(event.is_publicly_viewable)
        self.assertEqual(event.remaining_seats, 100)

    def test_event_validation_end_time_before_start_time(self):
        start = timezone.now() + timedelta(days=5)
        end = start - timedelta(hours=1)  # Invalid: ends before starts
        event = Event(
            title="Invalid Time Event",
            category=self.category,
            organizer=self.organizer,
            venue="Room 101",
            start_datetime=start,
            end_datetime=end,
            registration_deadline=start - timedelta(days=1),
            capacity=50,
        )
        with self.assertRaises(ValidationError):
            event.clean()

    def test_event_validation_deadline_after_start_time(self):
        start = timezone.now() + timedelta(days=5)
        end = start + timedelta(hours=2)
        deadline = start + timedelta(hours=1)  # Invalid: deadline after event start
        event = Event(
            title="Invalid Deadline Event",
            category=self.category,
            organizer=self.organizer,
            venue="Room 101",
            start_datetime=start,
            end_datetime=end,
            registration_deadline=deadline,
            capacity=50,
        )
        with self.assertRaises(ValidationError):
            event.clean()

    def test_registration_uniqueness_and_token(self):
        start = timezone.now() + timedelta(days=2)
        event = Event.objects.create(
            title="AI Workshop",
            category=self.category,
            organizer=self.organizer,
            venue="Auditorium",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            registration_deadline=start - timedelta(hours=2),
            capacity=30,
            status=EventStatus.APPROVED,
            is_published=True,
        )

        reg = Registration.objects.create(
            event=event,
            student=self.student,
        )
        self.assertIsNotNone(reg.ticket_token)
        self.assertEqual(len(reg.ticket_token), 32)
        self.assertEqual(event.remaining_seats, 29)

        # Duplicate registration by same student for same event must be blocked by DB constraint
        with self.assertRaises(IntegrityError):
            Registration.objects.create(
                event=event,
                student=self.student,
            )

    def test_attendance_one_to_one_constraint(self):
        start = timezone.now() + timedelta(days=1)
        event = Event.objects.create(
            title="Design Thinking",
            category=self.category,
            organizer=self.organizer,
            venue="Design Lab",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            registration_deadline=start - timedelta(hours=1),
            capacity=20,
            status=EventStatus.APPROVED,
            is_published=True,
        )
        reg = Registration.objects.create(event=event, student=self.student)

        # First check-in succeeds
        att = Attendance.objects.create(
            registration=reg,
            checked_in_by=self.organizer,
            method=CheckInMethod.QR_SCAN,
        )
        self.assertIsNotNone(att.id)
        self.assertTrue(reg.is_checked_in)

        # Second check-in for the same registration must be blocked by OneToOne constraint
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(
                registration=reg,
                checked_in_by=self.organizer,
                method=CheckInMethod.MANUAL,
            )

    def test_review_rating_and_uniqueness(self):
        start = timezone.now() - timedelta(days=2)
        event = Event.objects.create(
            title="Past Music Fest",
            category=self.category,
            organizer=self.organizer,
            venue="Amphitheatre",
            start_datetime=start,
            end_datetime=start + timedelta(hours=4),
            registration_deadline=start - timedelta(days=1),
            capacity=200,
            status=EventStatus.COMPLETED,
            is_published=True,
        )

        # Valid review
        review = Review.objects.create(
            event=event,
            student=self.student,
            rating=5,
            comment="Incredible event and production quality!",
        )
        self.assertEqual(review.rating, 5)

        # Duplicate review by same student on same event must be blocked
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                event=event,
                student=self.student,
                rating=4,
                comment="Another review attempt",
            )

    def test_audit_log_helper(self):
        log = AuditLog.log(
            actor=self.organizer,
            action="event_updated",
            object_type="Event",
            object_id="101",
            metadata={"changes": "Updated venue to Amphitheatre"},
        )
        self.assertEqual(log.action, "event_updated")
        self.assertEqual(log.object_id, "101")
        self.assertEqual(log.metadata["changes"], "Updated venue to Amphitheatre")
