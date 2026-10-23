# MUJVERSE — MUJ Campus Events & Experiences Platform
> **Tagline:** Your Campus. Your Universe.  
> **Institution:** Manipal University Jaipur (MUJ)  
> **Stack:** Python 3.14 / Django 5.2 LTS / MySQL 8 / Bootstrap 5 / Vanilla JavaScript  

---

## 🚀 Overview

MUJVERSE is a centralized campus community and event platform for Manipal University Jaipur. It allows students to discover campus events, register for free, receive cryptographically unique QR passes, and seamlessly check in at venues. Organizers manage registrations, track capacity, and scan tickets. Administrators moderate content, approve events, and review platform audits.

---

## 🏛 Architecture & Project Layout

```text
MUJVerse/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── mujverse/
│   ├── config/
│   │   ├── settings.py          # Production & dev settings (python-decouple)
│   │   ├── urls.py              # Root router
│   │   └── wsgi.py / asgi.py
│   ├── apps/
│   │   ├── accounts/            # Profiles, User model extension, 3 roles, auth, signals
│   │   ├── events/              # Categories & Events with state machine & validation
│   │   ├── registrations/       # Free registrations, UUID ticket tokens, constraints
│   │   ├── attendance/          # OneToOne atomic check-in, scanner terminal
│   │   ├── notifications/       # In-app notifications, services & global context processor
│   │   ├── reviews/             # Post-event attendee feedback (1–5 stars, one per student)
│   │   └── moderation/          # Event reports, report resolution & tamper-resistant AuditLog
│   ├── templates/               # Responsive HTML5 & Bootstrap 5 design system
│   │   ├── base.html            # Navigation, alerts, footer, theme tokens
│   │   ├── public/              # Home, explore, event details, categories, about, help
│   │   ├── accounts/            # Register, login, profile, password reset
│   │   ├── student/             # Student dashboard, registrations, QR ticket pass, notifications
│   │   ├── organizer/           # Organizer dashboard, Chart.js analytics, check-in scanner
│   │   ├── reviews/             # Review form
│   │   └── admin_dashboard/     # Platform admin dashboard, users, categories, reports, audit log
│   ├── static/
│   │   ├── css/mujverse.css     # Midnight indigo, electric violet & cyan accents
│   │   └── js/mujverse.js       # CSRF helpers, UI utilities
│   └── tests/
│       ├── test_accounts.py     # Auth, role isolation & anti-privilege escalation tests
│       ├── test_models.py       # Domain models, database constraints & validation tests
│       ├── test_events.py       # Event lifecycle, moderation, visibility & workflow tests
│       ├── test_phase3.py       # Registration, QR tickets, attendance & CSV export tests
│       └── test_phase4.py       # Notifications, reviews, admin actions & dashboard scoping
└── academic_modules/            # Supplementary syllabus demos (Phase 6)
```

---

## ⚙️ Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### Environment Variables Reference

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | *(placeholder)* | Cryptographic signing secret |
| `DJANGO_DEBUG` | `True` | Debug mode (set `False` in production) |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Host validation |
| `DB_ENGINE` | `django.db.backends.mysql` | Database engine (`mysql` required for production) |
| `DB_NAME` | `mujverse_db` | MySQL database name |
| `DB_USER` | `mujverse_user` | MySQL username |
| `DB_PASSWORD` | `your-password` | MySQL password |
| `DB_HOST` | `127.0.0.1` | MySQL server host |
| `DB_PORT` | `3306` | MySQL port |
| `EMAIL_HOST` | *(unset)* | Optional SMTP host — email notifications only dispatch when set |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_HOST_USER` | *(unset)* | SMTP username |
| `EMAIL_HOST_PASSWORD` | *(unset)* | SMTP password |

---

## 🗄 MySQL Database Setup

1. **Start MySQL 8 Server** on `127.0.0.1:3306`.
2. Create the database and user in MySQL console:
   ```sql
   CREATE DATABASE mujverse_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'mujverse_user'@'localhost' IDENTIFIED BY 'StrongPassword123!';
   GRANT ALL PRIVILEGES ON mujverse_db.* TO 'mujverse_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Create initial administrator:
   ```bash
   python manage.py createsuperuser
   ```

*(Note: When running isolated unit tests in environments where the local MySQL service is offline, set `$env:DB_ENGINE="django.db.backends.sqlite3"` to run the test runner in-memory.)*

---

## 🧪 Running Automated Tests

Run the full test suite (**99 automated tests**) covering authentication, role isolation, constraints, event management lifecycle, free registration, QR tickets, attendance check-in, CSV export, notifications, reviews, and admin controls:

```bash
python manage.py test mujverse.tests
```

*(For testing without a running MySQL instance, prepend `$env:DB_ENGINE="django.db.backends.sqlite3"` in PowerShell.)*

### Test Coverage Highlights — Phases 1–4

**Foundation & Auth (Phase 1)**
- ✅ Automatic profile creation via `post_save` signal (default least-privileged `student` role).
- ✅ Superuser creation auto-assignment of `admin` role.
- ✅ Anti-privilege escalation: public registration strictly enforces student role and strips injected permissions.
- ✅ Server-side authorization decorators (`@student_required`, `@organizer_required`, `@admin_required`) return HTTP 403 when violated.

**Event Management (Phase 2)**
- ✅ Cross-organizer access protection: organizers cannot view, edit, submit, or delete events belonging to others.
- ✅ Event scheduling validation: `end_datetime` must be after `start_datetime`; `registration_deadline` cannot exceed `start_datetime`.
- ✅ Event lifecycle: Draft ➔ Pending ➔ Approved/Rejected ➔ Resubmission workflow.
- ✅ Admin moderation: rejection mandates documented reasons; approvals & rejections generate immutable `AuditLog` entries.
- ✅ Public event discovery: only approved and published events appear on the homepage and explore directory.

**Registration, QR Tickets & Attendance (Phase 3)**
- ✅ Concurrency-safe free registration: `select_for_update()` transaction locking prevents capacity oversubscription under simultaneous requests.
- ✅ Deadlines & eligibility: rejects registrations for draft/unapproved, expired, concluded, or full events.
- ✅ Database constraints: unique `(event, student)` registration and unpredictable 32-character hexadecimal `ticket_token`.
- ✅ Re-registration after cancellation: students who previously cancelled can re-claim seats if capacity allows.
- ✅ QR code generation: high-resolution PNG QR codes encode only opaque tokens with zero personal credentials or PII.
- ✅ Ticket access control: students can view only their own passes; cross-student access is denied (HTTP 403).
- ✅ Cancellation policy: students can cancel passes and immediately release capacity, but cannot cancel after check-in or event conclusion.
- ✅ Atomic check-in verification: backend terminal rejects invalid, cancelled, wrong-event, or already-verified passes with exact error codes.
- ✅ Single-use attendance check-in: `OneToOne` link between `Registration` and `Attendance` prevents duplicate check-ins.
- ✅ Attendee management & CSV export: organizers can filter attendee rosters and export CSVs sanitized against spreadsheet formula injection (`=`, `+`, `-`, `@`).

**Dashboards, Notifications, Reviews & Admin Controls (Phase 4)**
- ✅ In-app notification creation on registration, check-in, event approval/rejection, and new reviews.
- ✅ Notification ownership isolation: students can only read and mark their own notifications; cross-user access returns HTTP 404.
- ✅ Mark-single and mark-all-as-read notification actions.
- ✅ Optional email: `notify()` only dispatches email when `EMAIL_HOST` is configured — never pretends mail was sent.
- ✅ Post-event reviews: only concluded-event attendees with confirmed registrations can submit reviews.
- ✅ One review per student per event enforced at both application and database level.
- ✅ Review comment validation: minimum 10 characters, maximum 1 000 characters; invalid submissions re-render form with field errors.
- ✅ Organizer review isolation: organizers can only inspect reviews for their own events (HTTP 403 for others).
- ✅ Admin user suspension & reactivation with `AuditLog` trail; self-suspension blocked at server level.
- ✅ Admin category creation and active/inactive toggle with `AuditLog` trail.
- ✅ Report moderation: admin can resolve or dismiss open reports with notes; `AuditLog` recorded for both actions.
- ✅ Dashboard scoping: organizer dashboard strictly shows only own events; student dashboard shows only own registrations.
- ✅ Non-admin access to admin dashboard returns HTTP 403 (students and organizers both blocked).

---

## 🎪 Seed Demonstration Data

Populate the database with default MUJ event categories and realistic campus events (Technical, Cultural, Sports, Workshops, E-Summit, etc.):

```bash
python manage.py seed_data
```

This command is safe and idempotent.

---

## 🎨 Design System

- **Primary Canvas:** Midnight Indigo (`#070913`, `#0c1022`, `#131936`)
- **Primary Brand Accent:** Electric Violet (`#7c3aed`, `#8b5cf6`)
- **Interactive Highlight:** Cyan (`#06b6d4`, `#22d3ee`)
- **Typography:** *Outfit* (headings) & *Inter* (body text)
- **Framework:** Bootstrap 5.3 + Bootstrap Icons + Custom Vanilla CSS & JS
- **Charts:** Chart.js (database-backed metrics only — no placeholder statistics)
