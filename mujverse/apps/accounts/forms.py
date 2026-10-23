"""
MUJVERSE — Authentication & Profile Forms
Strictly prevents privilege escalation: public registration is student-only.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from .models import Profile, RoleChoices


class StudentRegistrationForm(forms.ModelForm):
    """
    Public student registration form.
    Only creates accounts with the STUDENT role.
    Role and administrative flags are completely inaccessible here.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Create a strong password", "class": "form-control"}),
        label="Password",
        min_length=8,
        help_text="Minimum 8 characters. Must contain letters and numbers.",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Re-enter your password", "class": "form-control"}),
        label="Confirm Password",
    )
    student_identifier = forms.CharField(
        max_length=32,
        required=True,
        label="Registration / Student ID",
        widget=forms.TextInput(attrs={"placeholder": "e.g., 229301234", "class": "form-control"}),
        help_text="Your official MUJ registration number.",
    )
    department = forms.CharField(
        max_length=120,
        required=True,
        label="Academic Department",
        widget=forms.TextInput(attrs={"placeholder": "e.g., Computer Science & Engineering", "class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Choose a username", "class": "form-control"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@muj.manipal.edu", "class": "form-control"}),
            "first_name": forms.TextInput(attrs={"placeholder": "First Name", "class": "form-control"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last Name", "class": "form-control"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise ValidationError("An email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_student_identifier(self):
        sid = self.cleaned_data.get("student_identifier", "").strip()
        if Profile.objects.filter(student_identifier__iexact=sid).exists():
            raise ValidationError("This Student ID is already associated with an account.")
        return sid

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # Explicitly enforce non-staff, non-superuser
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            # Enforce student role on public registration
            profile.role = RoleChoices.STUDENT
            profile.display_name = f"{user.first_name} {user.last_name}".strip() or user.username
            profile.student_identifier = self.cleaned_data.get("student_identifier")
            profile.department = self.cleaned_data.get("department")
            profile.save()
            user.profile = profile
        return user


class UserLoginForm(AuthenticationForm):
    """
    Standard Django authentication form with enhanced styling and security.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Username or Student ID",
            "autocomplete": "username",
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Enter your password",
            "autocomplete": "current-password",
        })
    )


class UserProfileUpdateForm(forms.ModelForm):
    """
    Allows user to update personal info. Does NOT allow role or privilege changes.
    """
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))

    class Meta:
        model = Profile
        fields = ["display_name", "department", "bio", "profile_image"]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "profile_image": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name
            self.fields["email"].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise ValidationError("Another account already uses this email address.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data.get("first_name", "")
            self.user.last_name = self.cleaned_data.get("last_name", "")
            self.user.email = self.cleaned_data.get("email", "")
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile
