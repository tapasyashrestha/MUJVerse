"""
MUJVERSE — Authentication & Accounts Unit Tests
Tests student registration, role assignment, login/logout, and server-side authorization.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from mujverse.apps.accounts.models import Profile, RoleChoices
from mujverse.apps.accounts.forms import StudentRegistrationForm


class AccountsModelAndSignalTests(TestCase):
    def test_user_creation_auto_creates_student_profile(self):
        """Standard user creation should automatically attach a Profile with role=student."""
        user = User.objects.create_user(
            username="student_raj",
            email="raj@muj.manipal.edu",
            password="StrongPassword123!",
        )
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.role, RoleChoices.STUDENT)
        self.assertTrue(user.profile.is_student)
        self.assertFalse(user.profile.is_organizer)
        self.assertFalse(user.profile.is_admin)

    def test_superuser_creation_auto_creates_admin_profile(self):
        """Superuser creation should automatically assign ADMIN role."""
        admin_user = User.objects.create_superuser(
            username="super_admin",
            email="admin@muj.manipal.edu",
            password="SuperPassword123!",
        )
        self.assertTrue(hasattr(admin_user, "profile"))
        self.assertEqual(admin_user.profile.role, RoleChoices.ADMIN)
        self.assertTrue(admin_user.profile.is_admin)


class AccountsFormTests(TestCase):
    def test_public_registration_creates_student_only(self):
        """Registration form must never accept role input and must create a student account."""
        form_data = {
            "username": "student_ananya",
            "email": "ananya@muj.manipal.edu",
            "first_name": "Ananya",
            "last_name": "Sharma",
            "student_identifier": "229301001",
            "department": "Computer Science & Engineering",
            "password": "ValidPassword99#",
            "confirm_password": "ValidPassword99#",
            # Attempt privilege escalation via injected fields:
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
        }
        form = StudentRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        # Verify that elevated privileges were completely rejected
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.profile.role, RoleChoices.STUDENT)
        self.assertEqual(user.profile.student_identifier, "229301001")
        self.assertEqual(user.profile.department, "Computer Science & Engineering")

    def test_password_mismatch_rejected(self):
        form_data = {
            "username": "mismatch_user",
            "email": "mismatch@muj.manipal.edu",
            "first_name": "Test",
            "last_name": "User",
            "student_identifier": "229301002",
            "department": "IT",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
        }
        form = StudentRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)


class AccountsViewAndAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student_user = User.objects.create_user(
            username="test_student",
            email="student@muj.manipal.edu",
            password="TestPassword123!",
        )
        self.organizer_user = User.objects.create_user(
            username="test_organizer",
            email="organizer@muj.manipal.edu",
            password="TestPassword123!",
        )
        self.organizer_user.profile.role = RoleChoices.ORGANIZER
        self.organizer_user.profile.save()

        self.admin_user = User.objects.create_superuser(
            username="test_admin",
            email="admin@muj.manipal.edu",
            password="TestPassword123!",
        )

    def test_login_success(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "test_student",
            "password": "TestPassword123!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "test_student",
            "password": "WrongPassword!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout(self):
        self.client.login(username="test_student", password="TestPassword123!")
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_redirect_by_role(self):
        # Student redirect
        self.client.login(username="test_student", password="TestPassword123!")
        res_student = self.client.get(reverse("accounts:dashboard_redirect"))
        self.assertRedirects(res_student, reverse("student:dashboard"))
        self.client.logout()

        # Organizer redirect
        self.client.login(username="test_organizer", password="TestPassword123!")
        res_org = self.client.get(reverse("accounts:dashboard_redirect"))
        self.assertRedirects(res_org, reverse("organizer:dashboard"))
        self.client.logout()

        # Admin redirect
        self.client.login(username="test_admin", password="TestPassword123!")
        res_admin = self.client.get(reverse("accounts:dashboard_redirect"))
        self.assertRedirects(res_admin, reverse("platform_admin:dashboard"))

    def test_server_side_authorization_enforcement(self):
        """Student must be forbidden (403) from accessing admin or organizer dashboards."""
        self.client.login(username="test_student", password="TestPassword123!")
        res_admin = self.client.get(reverse("platform_admin:dashboard"))
        self.assertEqual(res_admin.status_code, 403)

        res_org = self.client.get(reverse("organizer:dashboard"))
        self.assertEqual(res_org.status_code, 403)
