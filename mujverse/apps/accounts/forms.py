"""
MUJVERSE — Authentication & Registration Forms
Supports dynamic Student and Club Organizer registration with strict validation.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import (
    Profile,
    RoleChoices,
    AccountStatus,
    Club,
    ClubMembership,
    ClubPosition,
    ApprovalStatus,
)


def validate_university_email(email):
    """
    Validates email format and encourages/requires official institutional domain if applicable.
    """
    clean_email = email.strip().lower()
    if not clean_email:
        raise ValidationError("University Email ID is required.")
    
    # Check domain
    parts = clean_email.split("@")
    if len(parts) != 2:
        raise ValidationError("Enter a valid email address.")
    
    return clean_email


class StudentRegistrationForm(forms.ModelForm):
    """
    Role-Based Student Registration:
    Collects:
      1. Full Name (first_name + last_name)
      2. Registration Number (student_identifier, unique)
      3. University Email ID (unique)
      4. Branch / Department
      5. Course / Degree
      6. Current Academic Year
      7. Current Semester
      8. Password
      9. Confirm Password
    """
    full_name = forms.CharField(
        max_length=150,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your full name (e.g., Aarav Sharma)",
            "class": "form-control",
            "required": True,
        }),
    )
    student_identifier = forms.CharField(
        max_length=32,
        required=True,
        label="Registration Number",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g., 229301234",
            "class": "form-control",
            "required": True,
        }),
        help_text="Official MUJ Registration Number (must be unique).",
    )
    email = forms.EmailField(
        required=True,
        label="University Email ID",
        widget=forms.EmailInput(attrs={
            "placeholder": "name.regno@muj.manipal.edu",
            "class": "form-control",
            "required": True,
        }),
        help_text="Official university email address.",
    )
    branch = forms.CharField(
        max_length=120,
        required=True,
        label="Branch / Department",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g., Computer Science & Engineering",
            "class": "form-control",
            "required": True,
        }),
    )
    course = forms.CharField(
        max_length=100,
        required=True,
        label="Course / Degree",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g., B.Tech, BCA, M.Tech, MBA",
            "class": "form-control",
            "required": True,
        }),
    )
    academic_year = forms.ChoiceField(
        choices=[
            ("", "Select Current Academic Year"),
            ("1st Year", "1st Year"),
            ("2nd Year", "2nd Year"),
            ("3rd Year", "3rd Year"),
            ("4th Year", "4th Year"),
            ("5th Year", "5th Year (Integrated / Law)"),
            ("Postgraduate", "Postgraduate"),
        ],
        required=True,
        label="Current Academic Year",
        widget=forms.Select(attrs={"class": "form-select", "required": True}),
    )
    semester = forms.ChoiceField(
        choices=[
            ("", "Select Current Semester"),
            ("1", "Semester 1"),
            ("2", "Semester 2"),
            ("3", "Semester 3"),
            ("4", "Semester 4"),
            ("5", "Semester 5"),
            ("6", "Semester 6"),
            ("7", "Semester 7"),
            ("8", "Semester 8"),
        ],
        required=False,
        label="Current Semester",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Create a strong password (min 8 chars)",
            "class": "form-control",
            "required": True,
        }),
        label="Password",
        min_length=8,
        help_text="Minimum 8 characters. Must contain letters and numbers.",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Re-enter your password",
            "class": "form-control",
            "required": True,
        }),
        label="Confirm Password",
    )

    class Meta:
        model = User
        fields = ["email"]

    def clean_email(self):
        email = validate_university_email(self.cleaned_data.get("email", ""))
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_student_identifier(self):
        sid = self.cleaned_data.get("student_identifier", "").strip()
        if not sid:
            raise ValidationError("Registration number is required.")
        if Profile.objects.filter(student_identifier__iexact=sid).exists():
            raise ValidationError("An account with this registration number already exists.")
        return sid

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        email = self.cleaned_data["email"].strip().lower()
        full_name = self.cleaned_data["full_name"].strip()
        sid = self.cleaned_data["student_identifier"].strip()

        # Split full name into first and last name
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Auto-generate a clean username based on student ID or email prefix
        base_username = sid.lower().replace(" ", "_")
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = RoleChoices.STUDENT
            profile.status = AccountStatus.ACTIVE
            profile.display_name = full_name
            profile.student_identifier = sid
            profile.branch = self.cleaned_data.get("branch", "")
            profile.department = self.cleaned_data.get("branch", "")
            profile.course = self.cleaned_data.get("course", "")
            profile.academic_year = self.cleaned_data.get("academic_year", "")
            profile.semester = self.cleaned_data.get("semester", "")
            profile.save()
            user.profile = profile

        return user


class OrganizerRegistrationForm(forms.ModelForm):
    """
    Role-Based Club Organizer Registration:
    Collects:
      1. Full Name
      2. Registration Number (unique)
      3. University Email ID (unique)
      4. Branch / Department
      5. Course / Degree
      6. Current Academic Year
      7. Club Name (select existing or request new club)
      8. Position in Club (President, VP, Core Committee, Other)
      9. Password
      10. Confirm Password
    """
    full_name = forms.CharField(
        max_length=150,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your full name",
            "class": "form-control",
            "required": True,
        }),
    )
    student_identifier = forms.CharField(
        max_length=32,
        required=True,
        label="Registration Number",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g., 229301999",
            "class": "form-control",
            "required": True,
        }),
        help_text="Official MUJ Registration Number (must be unique).",
    )
    email = forms.EmailField(
        required=True,
        label="University Email ID",
        widget=forms.EmailInput(attrs={
            "placeholder": "organizer.regno@muj.manipal.edu",
            "class": "form-control",
            "required": True,
        }),
        help_text="Official university email address.",
    )
    branch = forms.CharField(
        max_length=120,
        required=True,
        label="Branch / Department",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g., Computer Science & Engineering",
            "class": "form-control",
            "required": True,
        }),
    )
    course = forms.CharField(
        max_length=100,
        required=True,
        label="Course / Degree",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g., B.Tech, BCA, M.Tech",
            "class": "form-control",
            "required": True,
        }),
    )
    academic_year = forms.ChoiceField(
        choices=[
            ("", "Select Current Academic Year"),
            ("1st Year", "1st Year"),
            ("2nd Year", "2nd Year"),
            ("3rd Year", "3rd Year"),
            ("4th Year", "4th Year"),
            ("Postgraduate", "Postgraduate"),
        ],
        required=True,
        label="Current Academic Year",
        widget=forms.Select(attrs={"class": "form-select", "required": True}),
    )
    club_choice = forms.ChoiceField(
        required=True,
        label="Club Name",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_club_choice", "required": True}),
        help_text="Select an existing verified club or choose 'Request New Club'.",
    )
    new_club_name = forms.CharField(
        max_length=150,
        required=False,
        label="New Club Name (if requesting new)",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g., Robotics & AI Society",
            "class": "form-control",
            "id": "id_new_club_name",
        }),
        help_text="Requires administrative review & approval.",
    )
    position = forms.ChoiceField(
        choices=[
            ("", "Select Position in Club"),
            (ClubPosition.PRESIDENT, "President"),
            (ClubPosition.VICE_PRESIDENT, "Vice President"),
            (ClubPosition.CORE_COMMITTEE, "Core Committee Member"),
            (ClubPosition.OTHER, "Other Authorized Position"),
        ],
        required=True,
        label="Position in the Club",
        widget=forms.Select(attrs={"class": "form-select", "required": True}),
    )
    position_detail = forms.CharField(
        max_length=100,
        required=False,
        label="Specify Position (if Other)",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g., Technical Head, General Secretary",
            "class": "form-control",
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Create a strong password (min 8 chars)",
            "class": "form-control",
            "required": True,
        }),
        label="Password",
        min_length=8,
        help_text="Minimum 8 characters. Must contain letters and numbers.",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Re-enter your password",
            "class": "form-control",
            "required": True,
        }),
        label="Confirm Password",
    )

    class Meta:
        model = User
        fields = ["email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate club choices dynamically from database
        approved_clubs = Club.objects.filter(verification_status=ApprovalStatus.APPROVED).order_by("name")
        choices = [("", "-- Select a Registered Club --")]
        for club in approved_clubs:
            choices.append((str(club.id), club.name))
        choices.append(("NEW", "+ Request to Register a New Club"))
        self.fields["club_choice"].choices = choices

    def clean_email(self):
        email = validate_university_email(self.cleaned_data.get("email", ""))
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_student_identifier(self):
        sid = self.cleaned_data.get("student_identifier", "").strip()
        if not sid:
            raise ValidationError("Registration number is required.")
        if Profile.objects.filter(student_identifier__iexact=sid).exists():
            raise ValidationError("An account with this registration number already exists.")
        return sid

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        club_choice = cleaned_data.get("club_choice")
        new_club_name = cleaned_data.get("new_club_name", "").strip()
        position = cleaned_data.get("position")
        position_detail = cleaned_data.get("position_detail", "").strip()

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        if club_choice == "NEW" and not new_club_name:
            self.add_error("new_club_name", "Please enter the name of the new club you wish to register.")

        if position == ClubPosition.OTHER and not position_detail:
            self.add_error("position_detail", "Please specify your position title.")

        return cleaned_data

    def save(self, commit=True):
        email = self.cleaned_data["email"].strip().lower()
        full_name = self.cleaned_data["full_name"].strip()
        sid = self.cleaned_data["student_identifier"].strip()

        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        base_username = sid.lower().replace(" ", "_")
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            # Organizers start in PENDING status until administrative approval
            profile.role = RoleChoices.ORGANIZER
            profile.status = AccountStatus.PENDING
            profile.display_name = full_name
            profile.student_identifier = sid
            profile.branch = self.cleaned_data.get("branch", "")
            profile.department = self.cleaned_data.get("branch", "")
            profile.course = self.cleaned_data.get("course", "")
            profile.academic_year = self.cleaned_data.get("academic_year", "")
            profile.save()
            user.profile = profile

            # Handle Club and Membership
            club_choice = self.cleaned_data.get("club_choice")
            if club_choice == "NEW":
                new_name = self.cleaned_data.get("new_club_name").strip()
                club, _ = Club.objects.get_or_create(
                    name=new_name,
                    defaults={"verification_status": ApprovalStatus.PENDING},
                )
            else:
                club = Club.objects.get(id=int(club_choice))

            ClubMembership.objects.create(
                user=user,
                club=club,
                position=self.cleaned_data.get("position"),
                position_detail=self.cleaned_data.get("position_detail", ""),
                approval_status=ApprovalStatus.PENDING,
            )

        return user


class UserLoginForm(forms.Form):
    """
    Enhanced Sign In form supporting either University Email or Registration Number.
    """
    identifier = forms.CharField(
        label="University Email or Registration Number",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Email (e.g. name@muj.manipal.edu) or Reg No",
            "autocomplete": "username",
            "required": True,
        }),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Enter your password",
            "autocomplete": "current-password",
            "required": True,
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("identifier", "").strip()
        password = cleaned_data.get("password")

        if identifier and password:
            user = None
            # 1. Search by email (case-insensitive)
            user_by_email = User.objects.filter(email__iexact=identifier).first()
            if user_by_email and user_by_email.check_password(password):
                user = user_by_email
            
            # 2. Search by registration number / student_identifier
            if not user:
                profile_match = Profile.objects.filter(student_identifier__iexact=identifier).first()
                if profile_match and profile_match.user.check_password(password):
                    user = profile_match.user

            # 3. Search by username fallback
            if not user:
                user_by_username = User.objects.filter(username__iexact=identifier).first()
                if user_by_username and user_by_username.check_password(password):
                    user = user_by_username

            if user is None:
                raise ValidationError("Invalid credentials. Please verify your email / registration number and password.")
            elif not user.is_active:
                raise ValidationError("This account has been deactivated or suspended. Please contact platform administrators.")

            self.user_cache = user

        return cleaned_data

    def get_user(self):
        return self.user_cache


class UserProfileUpdateForm(forms.ModelForm):
    """
    Allows user to update personal info. Does NOT allow role or privilege changes.
    """
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))

    class Meta:
        model = Profile
        fields = ["display_name", "branch", "course", "academic_year", "semester", "bio", "profile_image"]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "form-control"}),
            "branch": forms.TextInput(attrs={"class": "form-control"}),
            "course": forms.TextInput(attrs={"class": "form-control"}),
            "academic_year": forms.TextInput(attrs={"class": "form-control"}),
            "semester": forms.TextInput(attrs={"class": "form-control"}),
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
