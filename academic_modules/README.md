# MUJVERSE — Academic Modules Documentation & Viva Guide
======================================================

This directory contains functional, isolated academic demonstrations for technologies and concepts required by academic syllabi (such as Web Technologies, Internet Applications, and Full-Stack Development) that are intentionally isolated from the core production Django application.

---

## Syllabus Mapping Table

| Academic Technology / Requirement | Location in Codebase | Type of Module | Verification Command |
|---|---|---|---|
| **1. Node.js + Express JSON API** | [`academic_modules/node_demo/`](file:///academic_modules/node_demo/) | Isolated REST API Service | `npm start` & `node test_requests.js` |
| **2. AngularJS 1.x MVC & Data Binding** | [`academic_modules/angularjs_demo/`](file:///academic_modules/angularjs_demo/) | Isolated Frontend Single-Page Demo | Open `index.html` in browser |
| **3. Python CGI & Safe Form Processing** | [`academic_modules/python_form_demo/`](file:///academic_modules/python_form_demo/) | Isolated HTTP Form Server | `python server.py` & `python test_form.py` |
| **4. jQuery AJAX & Lifecycle States** | [`academic_modules/jquery_ajax_demo/`](file:///academic_modules/jquery_ajax_demo/) | Isolated Frontend AJAX Demo | Open `index.html` via HTTP server |
| **5. XHTML 1.0 Strict (XML DTD Rules)** | [`academic_modules/xhtml_demo/`](file:///academic_modules/xhtml_demo/) | Strict XML Document & DTD | `python -c "import xml.etree.ElementTree as ET; ET.parse('academic_modules/xhtml_demo/index.xhtml')"` |
| **6. Fetch API & JSON Async (CSRF Safe)** | `mujverse/templates/student/notifications.html` & `notifications/views.py` | Core Django Integration | Browser interaction + `test_phase4.py` |
| **7. MySQL & Django Relational ORM** | `mujverse/apps/events/management/commands/demo_orm.py` | Management Command & Core ORM | `python manage.py demo_orm` |

---

## 1. Node.js + Express (`academic_modules/node_demo/`)

### Purpose
Demonstrates lightweight JavaScript back-end engineering using Node.js and Express to build RESTful microservices exposing structured JSON data.

### Features
- Express middleware routing (`express.json()`).
- Endpoints:
  - `GET /api/health` — System status, uptime, and timestamp.
  - `GET /api/events` — Filtering by category, search term, and pagination (`limit`, `offset`).
  - `GET /api/events/:id` — Route parameter validation (numeric ID checking) and 404 responses.
- Structured RFC-compliant JSON responses and proper HTTP status codes (`200 OK`, `400 Bad Request`, `404 Not Found`).

### How to Run
```bash
cd academic_modules/node_demo
npm install
npm start
# Server listens on http://localhost:3000
```

### Verification Command
In another terminal:
```bash
cd academic_modules/node_demo
node test_requests.js
```

### Viva / Academic Explanation
- **Why Node.js?** Node's single-threaded, non-blocking event loop (powered by V8 and libuv) excels at I/O-intensive operations and microservices.
- **REST Principles:** Utilizes HTTP verbs (GET) with standard resource paths and status codes.

---

## 2. AngularJS 1.x (`academic_modules/angularjs_demo/`)

### Purpose
Demonstrates the historical Model-View-Controller (MVC / MVVM) architecture that popularized client-side single page applications (SPAs) before modern component frameworks (React, Vue, Angular 2+).

### Features
- Module declaration (`angular.module("mujverseApp", [])`).
- Controller scope management (`ng-controller="EventExplorerController as vm"`).
- Two-way data binding (`ng-model="vm.searchQuery"`).
- Directives demonstrated: `ng-repeat`, `ng-if`, `ng-style`, `ng-click`.
- Client-side filtering and computed scope properties.

### How to Run
Simply open `academic_modules/angularjs_demo/index.html` in any modern web browser or serve it via a local HTTP server:
```bash
python -m http.server 8000 --directory academic_modules/angularjs_demo
# Open http://localhost:8000 in your browser
```

### Viva / Academic Explanation
- **Two-way Data Binding:** When the model changes, the view updates; when user input changes the view, the model updates automatically via the `$digest` cycle and "dirty checking".
- **Legacy Disclosure:** AngularJS 1.x reached End of Life (EOL) in December 2021. It is retained here strictly for academic syllabus alignment.

---

## 3. Python CGI & Safe Form Processing (`academic_modules/python_form_demo/`)

### Purpose
Demonstrates the classic HTTP Form / CGI request-response lifecycle in Python: parsing URL-encoded POST bodies, validating types, sanitizing inputs, and rendering response pages.

### Legacy Disclosure & PEP 594 Compatibility Note
> **Crucial Academic Note:** The historical `cgi` and `cgitb` modules were formally deprecated in Python 3.11 (PEP 594) and **completely removed in Python 3.13+**. Running `import cgi` in Python 3.13 or 3.14 raises a fatal `ModuleNotFoundError`.
> To provide 100% operational fidelity without obsolete broken standard libraries, this module uses Python's standard `http.server` and `urllib.parse` to cleanly simulate CGI form processing and request parsing.

### How to Run
```bash
cd academic_modules/python_form_demo
python server.py
# Server starts on http://localhost:8050
```

### Verification Command
In another terminal:
```bash
python academic_modules/python_form_demo/test_form.py
```
This tests:
1. `GET /health`
2. `GET /` (Form rendering)
3. `POST /submit` (Valid submission)
4. `POST /submit` (Rejection of invalid input format with HTTP 400)
5. `POST /submit` (XSS sanitization using `html.escape()`)

---

## 4. jQuery AJAX & Lifecycle States (`academic_modules/jquery_ajax_demo/`)

### Purpose
Demonstrates asynchronous JavaScript XML/JSON (AJAX) using jQuery's `$.ajax()` method and handling the complete network lifecycle.

### Features
- Explicit UI feedback for all network states:
  - **Loading:** In-flight spinner and status alert.
  - **Success:** Dynamic DOM injection of received JSON events.
  - **Empty:** Graceful notification when a filter returns zero matching records.
  - **Error:** Catching HTTP 404 and JSON parser failures (`parsererror`).

### How to Run
Run a local static server:
```bash
python -m http.server 8060 --directory academic_modules/jquery_ajax_demo
# Visit http://localhost:8060 in browser and click the scenario trigger buttons
```

### Viva / Academic Explanation
- **`$.ajax()` vs `fetch()`:** jQuery's `$.ajax()` automatically enters the `error` callback on HTTP 4xx/5xx status codes and auto-deserializes JSON if `dataType: 'json'` is specified. Modern native `fetch()` resolves promises even on HTTP 404/500 and requires manual checks (`response.ok`).

---

## 5. XHTML 1.0 Strict (`academic_modules/xhtml_demo/`)

### Purpose
Demonstrates the difference between modern forgiving HTML5 and strict XML-based XHTML 1.0.

### Features
- Adherence to W3C XHTML 1.0 Strict DTD.
- XML Declaration `<?xml version="1.0" encoding="UTF-8"?>`.
- Strictly lowercase element tags and attribute names.
- Explicit closing for all tags (e.g. self-closing void elements like `<br />` and `<hr />`).
- All attribute values quoted (`xml:lang="en"`).
- Styles and scripts wrapped in XML `<![CDATA[ ... ]]>` blocks.

### Verification Command
Verify well-formedness with Python's built-in XML parser:
```bash
python -c "import xml.etree.ElementTree as ET; ET.parse('academic_modules/xhtml_demo/index.xhtml'); print('Valid XHTML/XML!')"
```

---

## 6. JSON + Fetch API (Integrated in Core MUJVERSE)

### Purpose
Demonstrates modern asynchronous browser-to-server communication using standard ES6 `fetch()`, native JSON promises, and Django CSRF protection.

### Implementation in MUJVERSE
- **Endpoint:** `GET /notifications/unread-count/` returns `{"unread_count": N}`.
- **Action:** Marking notifications as read dynamically without page reloads via `POST /notifications/<id>/read/`.
- **Security:** Sends the `X-CSRFToken` request header retrieved safely from the DOM.
- **Progressive Enhancement:** If JavaScript is disabled, the forms fall back to standard HTML POST redirects seamlessly.

---

## 7. MySQL & Django ORM (`demo_orm` Command)

### Purpose
Demonstrates relational database management, schema integrity, and query generation in Django's Object-Relational Mapper (ORM) targeting MySQL.

### Demonstration Command
```bash
python manage.py demo_orm
```

### Key Concepts Covered
1. **Relational Constraints:**
   - `UniqueConstraint(fields=['event', 'student'])` on registrations.
   - `ForeignKey(..., on_delete=models.PROTECT)` on Categories to prevent orphan records.
2. **Aggregations & Annotations:**
   - `Count("events")` and `Avg("reviews__rating")` translating to SQL `GROUP BY` and `JOIN`.
3. **Query Inspection:**
   - Demonstrating how `.query` generates raw MySQL dialect SQL syntax.
