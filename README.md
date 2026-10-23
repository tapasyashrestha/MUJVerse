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
│   │   ├── wsgi.py & asgi.py
│   ├── apps/
│   │   ├── accounts/            # Profiles, User model extension, 3 roles, auth, signals
│   │   ├── events/              # Categories & Events with state machine & validation
│   │   ├── registrations/       # Free registrations, UUID ticket tokens, constraints
│   │   ├── attendance/          # OneToOne atomic check-in, scanner terminal
│   │   ├── notifications/       # In-app notifications & global context processor
│   │   ├── reviews/             # Post-event attendee feedback (1-5 stars)
│   │   └── moderation/          # Event reports & tamper-resistant AuditLog
│   ├── templates/               # Responsive HTML5 & Bootstrap 5 design system
│   │   ├── base.html            # Navigation, alerts, footer, theme tokens
│   │   ├── public/              # Home, explore, event details, categories, about, help
│   │   ├── accounts/            # Register, login, profile, password reset
│   │   ├── student/             # Student dashboard, registrations, QR ticket pass
│   │   ├── organizer/           # Organizer dashboard, check-in scanner
│   │   └── admin_dashboard/     # Platform admin dashboard, pending review queue
│   ├── static/
│   │   ├── css/mujverse.css     # Midnight indigo, electric violet & cyan accents
│   │   └── js/mujverse.js       # CSRF helpers, UI utilities
│   └── tests/
│       ├── test_accounts.py     # Auth, role isolation & anti-privilege escalation tests
│       └── test_models.py       # Domain models, database constraints & validation tests
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

*(Note: When running isolated unit tests in environments where the local MySQL service is offline, set `$env:DB_ENGINE="django.db.backends.sqlite3"` to run the test runner in-memory).*

---

## 🧪 Running Automated Tests

Run the full test suite (49 automated tests) covering authentication, role isolation, constraints, event management lifecycle, and admin moderation:

```bash
python manage.py test mujverse.tests
```

*(For testing without a running MySQL instance, prepend `$env:DB_ENGINE="django.db.backends.sqlite3"` in PowerShell).*

### Test Coverage Highlights:
- ✅ Automatic profile creation via `post_save` signal (default least-privileged `student` role).
- ✅ Superuser creation auto-assignment of `admin` role.
- ✅ Anti-privilege escalation: public registration strictly enforces student role and strips injected permissions.
- ✅ Server-side authorization decorators (`@student_required`, `@organizer_required`, `@admin_required`) return HTTP 403 when violated.
- ✅ Cross-organizer access protection: organizers cannot view, edit, submit, or delete events belonging to others.
- ✅ Event scheduling validation: `end_datetime` must be after `start_datetime`, `registration_deadline` cannot exceed `start_datetime`.
- ✅ Event lifecycle: Draft ➔ Pending ➔ Approved/Rejected ➔ Resubmission workflow.
- ✅ Admin moderation: Rejection mandates documented reasons; approvals & rejections generate immutable `AuditLog` entries.
- ✅ Public event discovery: Only approved and published events appear on the homepage and explore directory with live filtering and pagination.
- ✅ Database constraints: Unique `(event, student)` registration and unique `ticket_token`.
- ✅ Single-use attendance check-in: OneToOne link between `Registration` and `Attendance` prevents duplicate check-ins.

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

