"""
MUJVERSE — MySQL & Django ORM Academic Demonstration Management Command
========================================================================
Demonstrates relational modeling concepts in MUJVERSE:
1. Foreign Keys and Cascade / Protect relationships
2. Unique constraints (e.g. UniqueConstraint on Event + Student for Registration)
3. Relational filtering, lookups, and Q objects
4. Aggregate & Annotate queries (Count, Avg, remaining capacity)
5. Generation of underlying SQL statements
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, F, Q
from django.db import connection
from mujverse.apps.events.models import Event, Category, EventStatus
from mujverse.apps.registrations.models import Registration
from mujverse.apps.reviews.models import Review


class Command(BaseCommand):
    help = "Demonstrates MySQL & Django ORM relational queries, constraints, and aggregations."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("  MUJVERSE Academic Demonstration: MySQL & Django ORM"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        # 1. Relational Query & SQL inspection
        self.stdout.write("\n" + self.style.WARNING("1. Relational Filtering & SQL Inspection:"))
        events_qs = (
            Event.objects.filter(status=EventStatus.APPROVED)
            .select_related("category", "organizer")
            .only("title", "venue", "capacity", "category__name", "organizer__username")[:3]
        )
        self.stdout.write(f"Query SQL:\n  {events_qs.query}\n")

        # 2. Aggregations & Annotations
        self.stdout.write(self.style.WARNING("2. Aggregation & Annotation (GROUP BY in MySQL):"))
        categories_stats = (
            Category.objects.annotate(
                total_events=Count("events"),
                approved_events=Count("events", filter=Q(events__status=EventStatus.APPROVED)),
            )
            .values("name", "total_events", "approved_events")[:5]
        )
        self.stdout.write("Categories with annotated event counts:")
        for cat in categories_stats:
            self.stdout.write(f"  - {cat['name']}: {cat['total_events']} total ({cat['approved_events']} approved)")

        # 3. Capacity & Attendance metrics via ORM
        self.stdout.write("\n" + self.style.WARNING("3. Dynamic Registration & Capacity Calculation:"))
        annotated_events = (
            Event.objects.annotate(
                reg_count=Count("registrations", filter=Q(registrations__status="confirmed")),
                avg_rating=Avg("reviews__rating"),
            )
            .values("title", "capacity", "reg_count", "avg_rating")[:4]
        )
        for ev in annotated_events:
            seats_left = max(0, ev["capacity"] - ev["reg_count"])
            rating_display = f"{ev['avg_rating']:.1f}/5.0" if ev["avg_rating"] else "No reviews"
            self.stdout.write(
                f"  - {ev['title'][:32]:<32} | Cap: {ev['capacity']} | Reg: {ev['reg_count']} | Left: {seats_left} | Rating: {rating_display}"
            )

        # 4. Relational Constraints Summary
        self.stdout.write("\n" + self.style.WARNING("4. Integrity & Database Constraints in MUJVERSE:"))
        self.stdout.write("  - Registration: UniqueConstraint(fields=['event', 'student']) [Prevents duplicate registrations]")
        self.stdout.write("  - Attendance: UniqueConstraint(fields=['registration']) [Guarantees one check-in per ticket]")
        self.stdout.write("  - Review: UniqueConstraint(fields=['event', 'student']) [Ensures single review per attendee]")
        self.stdout.write("  - Foreign Keys with on_delete=PROTECT on Category to prevent orphan events.")

        self.stdout.write("\n" + self.style.SUCCESS("✓ MySQL & Django ORM Academic Demo executed successfully.\n"))
