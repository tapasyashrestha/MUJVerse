"""
MUJVERSE — Seed Data Management Command
Populates the database with categories and demo events for local development.
Usage: python manage.py seed_data [--events N] [--clear]
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from mujverse.apps.events.models import Category, Event, EventStatus


CATEGORIES = [
    {"name": "Cultural", "icon": "bi-music-note-beamed", "description": "Fests, dance, music, drama, and art performances."},
    {"name": "Technical", "icon": "bi-code-slash", "description": "Hackathons, coding challenges, and tech workshops."},
    {"name": "Sports", "icon": "bi-trophy", "description": "Intra-campus sports, tournaments, and fitness events."},
    {"name": "Workshops", "icon": "bi-tools", "description": "Skill-building workshops and professional development."},
    {"name": "Hackathons", "icon": "bi-lightning-charge", "description": "24-48 hour hackathons and innovation sprints."},
    {"name": "Academic", "icon": "bi-mortarboard", "description": "Guest lectures, seminars, and academic conferences."},
    {"name": "Social", "icon": "bi-people", "description": "Networking meetups, community drives, and fests."},
    {"name": "Entrepreneurship", "icon": "bi-graph-up-arrow", "description": "Startup competitions, pitch nights, and incubator events."},
]

DEMO_EVENTS = [
    {
        "title": "MUJ Hackathon 2026 — Build the Future",
        "description": (
            "Join 200+ developers, designers, and innovators for a 36-hour hackathon "
            "at MUJ's Innovation Hub. Solve real-world problems across tracks: AI/ML, "
            "FinTech, HealthTech, and GreenTech. Prizes worth ₹1,00,000 to be won. "
            "Open to all MUJ students. Team size: 2-4."
        ),
        "category": "Hackathons",
        "venue": "Innovation Hub, Block J",
        "days_from_now": 20,
        "duration_hours": 36,
        "deadline_days": 15,
        "capacity": 200,
    },
    {
        "title": "Spectrum 2026 — Annual Cultural Fest",
        "description": (
            "MUJVERSE's flagship annual cultural extravaganza returns! "
            "Spanning three action-packed days, Spectrum features battle of bands, "
            "solo performances, classical dance competitions, standup comedy, "
            "drama, and the iconic fashion show. Register your team or perform solo. "
            "All cultural enthusiasts are welcome!"
        ),
        "category": "Cultural",
        "venue": "Open Air Auditorium, Main Campus",
        "days_from_now": 35,
        "duration_hours": 72,
        "deadline_days": 25,
        "capacity": 1500,
    },
    {
        "title": "Web Development Bootcamp — React & Django",
        "description": (
            "An intensive two-day hands-on workshop covering modern full-stack web development. "
            "Day 1: Django REST Framework, databases, and deployment. "
            "Day 2: React fundamentals, state management, and connecting to APIs. "
            "Prerequisites: Basic Python and HTML knowledge. Bring your laptop."
        ),
        "category": "Workshops",
        "venue": "Computer Lab 3, Block C",
        "days_from_now": 10,
        "duration_hours": 16,
        "deadline_days": 7,
        "capacity": 40,
    },
    {
        "title": "Inter-Department Cricket Tournament",
        "description": (
            "The most anticipated cricket tournament of the semester is back! "
            "Register your department team for a 10-over T10 format competition. "
            "All departments are welcome. Matches will be held on the main ground. "
            "The winning team earns the coveted MUJ Cricket Shield."
        ),
        "category": "Sports",
        "venue": "Main Sports Ground",
        "days_from_now": 14,
        "duration_hours": 8,
        "deadline_days": 10,
        "capacity": 120,
    },
    {
        "title": "AI in Healthcare — Guest Lecture Series",
        "description": (
            "A special lecture by Dr. Arvind Sharma, AI Research Lead at AIIMS Delhi, "
            "on the transformative applications of machine learning in diagnostics, "
            "drug discovery, and personalized medicine. Q&A session included. "
            "Certificates of attendance will be provided to all registered participants."
        ),
        "category": "Academic",
        "venue": "Seminar Hall A, Admin Block",
        "days_from_now": 7,
        "duration_hours": 3,
        "deadline_days": 5,
        "capacity": 250,
    },
    {
        "title": "Startup Pitch Night — Investor Meet 2026",
        "description": (
            "Present your startup idea to a panel of investors, venture capitalists, "
            "and industry mentors from Bangalore and Delhi. Top 3 pitches win seed funding "
            "and 3-month incubation at MUJ Innovation Hub. Open to all students with a "
            "working prototype or MVP. Pitches are 5 minutes + 3 minutes Q&A."
        ),
        "category": "Entrepreneurship",
        "venue": "MUJ Innovation Hub Conference Room",
        "days_from_now": 28,
        "duration_hours": 5,
        "deadline_days": 20,
        "capacity": 100,
    },
]


class Command(BaseCommand):
    help = "Seed the database with demo categories and sample events for local development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove all existing events before seeding.",
        )
        parser.add_argument(
            "--events",
            type=int,
            default=len(DEMO_EVENTS),
            help="Number of demo events to create (default: all).",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            count, _ = Event.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {count} existing events."))

        # ── Categories ─────────────────────────────────────────
        self.stdout.write("Creating categories...")
        cat_map = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults={
                    "icon": cat_data["icon"],
                    "description": cat_data["description"],
                    "is_active": True,
                },
            )
            cat_map[cat.name] = cat
            status = "created" if created else "already exists"
            self.stdout.write(f"  {'✓' if created else '•'} {cat.name} ({status})")

        # ── Organizer account ───────────────────────────────────
        organizer, created = User.objects.get_or_create(
            username="demo_organizer",
            defaults={
                "email": "organizer@muj.manipal.edu",
                "first_name": "Demo",
                "last_name": "Organizer",
                "is_active": True,
            },
        )
        if created:
            organizer.set_password("DemoPass@123")
            organizer.save()
            organizer.profile.role = "organizer"
            organizer.profile.student_id = "ORG-2026"
            organizer.profile.save()
            self.stdout.write(self.style.SUCCESS("  ✓ Created organizer: demo_organizer / DemoPass@123"))
        else:
            self.stdout.write(f"  • Organizer demo_organizer already exists")

        # ── Events ──────────────────────────────────────────────
        self.stdout.write("\nCreating demo events...")
        now = timezone.now()
        events_to_create = DEMO_EVENTS[: options["events"]]

        created_count = 0
        for data in events_to_create:
            start = now + timedelta(days=data["days_from_now"])
            end = start + timedelta(hours=data["duration_hours"])
            deadline = now + timedelta(days=data["deadline_days"])
            category = cat_map.get(data["category"])
            if not category:
                self.stdout.write(self.style.WARNING(f"  ! Category '{data['category']}' not found. Skipping."))
                continue

            event, created = Event.objects.get_or_create(
                title=data["title"],
                defaults={
                    "description": data["description"],
                    "category": category,
                    "organizer": organizer,
                    "venue": data["venue"],
                    "start_datetime": start,
                    "end_datetime": end,
                    "registration_deadline": deadline,
                    "capacity": data["capacity"],
                    "status": EventStatus.APPROVED,
                    "is_published": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  ✓ {event.title}")
            else:
                self.stdout.write(f"  • {event.title} (already exists)")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Seed complete! "
                f"Categories: {len(CATEGORIES)}, "
                f"Events created: {created_count}/{len(events_to_create)}"
            )
        )
