"""
MUJVERSE Academic Demo — Python CGI / Safe Form Processing Simulation
=====================================================================
Educational Purpose:
Demonstrates traditional CGI / HTTP form processing concepts in modern Python:
- Parsing application/x-www-form-urlencoded POST data safely (via urllib.parse)
- Comprehensive server-side input validation and error feedback
- Safe HTML escaping (via html.escape) to prevent Cross-Site Scripting (XSS)
- Safe handling without invoking arbitrary code or shell commands
- Clean separation between GET (rendering the form) and POST (processing)

Compatibility Note:
The Python `cgi` and `cgitb` modules were deprecated in Python 3.11 (PEP 594)
and completely removed in Python 3.13+. On Python 3.13 / 3.14, any code attempting
`import cgi` raises ModuleNotFoundError.
This demo uses `http.server` and `urllib.parse` from Python's standard library to
faithfully simulate CGI form request-response lifecycle in a cross-version, safe manner.
"""

import html
import http.server
import json
import re
import socketserver
import urllib.parse
from datetime import datetime

PORT = 8050
EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$")
ROLL_REGEX = re.compile(r"^[0-9]{8,10}$")

REGISTRATIONS_LOG = []

HTML_FORM_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MUJVERSE — Python Form Processing Academic Demo</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .card { background: #1e293b; border: 1px solid #334155; }
    .form-control, .form-select { background: #0f172a; border-color: #334155; color: #f8fafc; }
    .form-control:focus, .form-select:focus { background: #0f172a; color: #fff; border-color: #3b82f6; box-shadow: 0 0 0 0.25rem rgba(59, 130, 246, 0.25); }
    .callout { background: rgba(59, 130, 246, 0.1); border-left: 4px solid #3b82f6; padding: 1rem; border-radius: 4px; }
  </style>
</head>
<body class="py-5">
  <div class="container" style="max-width: 800px;">
    <div class="mb-4">
      <span class="badge bg-primary mb-2">Academic Demo #3</span>
      <h1 class="h3 fw-bold text-white">Python HTTP Form Processing & Validation</h1>
      <p class="text-secondary small">
        Demonstrates safe server-side input handling, validation, sanitization (HTML escaping), and CGI-style request lifecycle.
      </p>
      <div class="callout mb-4">
        <h6 class="fw-semibold text-info mb-1">Legacy Note (Python 3.13+ Compatibility):</h6>
        <p class="small text-secondary mb-0">
          The historic <code>cgi</code> module was removed in Python 3.13 (PEP 594). This script uses standard <code>http.server</code> and <code>urllib.parse</code> to reliably simulate CGI form processing with zero external dependencies.
        </p>
      </div>
    </div>

    <!-- The Form -->
    <div class="card p-4 shadow-sm mb-4">
      <h5 class="fw-bold mb-3 text-white">Event Registration Form</h5>
      <form action="/submit" method="POST">
        <div class="mb-3">
          <label class="form-label" for="full_name">Full Name *</label>
          <input type="text" class="form-control" id="full_name" name="full_name" placeholder="e.g. Rahul Sharma" required maxlength="100">
        </div>

        <div class="row">
          <div class="col-md-6 mb-3">
            <label class="form-label" for="registration_no">Registration Number (Roll No) *</label>
            <input type="text" class="form-control" id="registration_no" name="registration_no" placeholder="e.g. 210905123" required maxlength="10">
            <div class="form-text text-secondary">8 to 10 digits only</div>
          </div>
          <div class="col-md-6 mb-3">
            <label class="form-label" for="email">Student Email *</label>
            <input type="email" class="form-control" id="email" name="email" placeholder="e.g. rahul@muj.manipal.edu" required maxlength="100">
          </div>
        </div>

        <div class="mb-3">
          <label class="form-label" for="event_choice">Select Event *</label>
          <select class="form-select" id="event_choice" name="event_choice" required>
            <option value="">-- Choose an event --</option>
            <option value="MUJ Hackathon 2026">MUJ Hackathon 2026 (Technical)</option>
            <option value="Symphony Night">Symphony Night (Cultural)</option>
            <option value="Inter-Department Football">Inter-Department Football (Sports)</option>
            <option value="AI & Robotics Workshop">AI & Robotics Workshop (Workshop)</option>
          </select>
        </div>

        <div class="mb-3">
          <label class="form-label" for="special_notes">Special Requirements / Notes (Optional)</label>
          <textarea class="form-control" id="special_notes" name="special_notes" rows="2" placeholder="Any dietary or seating preferences..." maxlength="300"></textarea>
        </div>

        <button type="submit" class="btn btn-primary px-4">Submit Registration</button>
      </form>
    </div>

    <div class="card p-4">
      <h6 class="fw-bold text-white mb-2">Registered Submissions in Current Session:</h6>
      <p class="small text-secondary">View past submissions stored in memory: <a href="/registrations.json" class="text-info" target="_blank">/registrations.json</a></p>
    </div>
  </div>
</body>
</html>
"""

def render_response_page(success: bool, title: str, messages: list, data: dict = None) -> str:
    color = "success" if success else "danger"
    status_text = "Registration Successful!" if success else "Validation Failed"

    data_rows = ""
    if data:
        for k, v in data.items():
            safe_k = html.escape(str(k))
            safe_v = html.escape(str(v))
            data_rows += f"<tr><th class='text-secondary'>{safe_k}</th><td><code>{safe_v}</code></td></tr>"

    msg_items = "".join([f"<li>{html.escape(m)}</li>" for m in messages])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MUJVERSE — Form Submission Result</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .card {{ background: #1e293b; border: 1px solid #334155; }}
  </style>
</head>
<body class="py-5">
  <div class="container" style="max-width: 700px;">
    <div class="card p-4 border-{color} shadow-sm">
      <div class="d-flex align-items-center mb-3">
        <span class="badge bg-{color} fs-6 me-2">{'PASS' if success else 'ERROR'}</span>
        <h4 class="mb-0 text-white">{status_text}</h4>
      </div>
      <p class="text-secondary">{html.escape(title)}</p>

      {'<ul class="text-danger">' + msg_items + '</ul>' if not success else '<ul class="text-success">' + msg_items + '</ul>'}

      {f'''
      <h6 class="mt-4 text-white fw-semibold">Processed & Sanitized Data (HTML Escaped):</h6>
      <table class="table table-dark table-sm table-bordered mt-2">
        <tbody>
          {data_rows}
        </tbody>
      </table>
      ''' if data else ''}

      <div class="mt-4">
        <a href="/" class="btn btn-outline-light btn-sm">&larr; Back to Form</a>
        <a href="/registrations.json" class="btn btn-outline-info btn-sm ms-2" target="_blank">View All (JSON)</a>
      </div>
    </div>
  </div>
</body>
</html>
"""

class FormHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default terminal request spam
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_FORM_PAGE.encode("utf-8"))
        elif parsed.path == "/registrations.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            payload = json.dumps({"count": len(REGISTRATIONS_LOG), "registrations": REGISTRATIONS_LOG}, indent=2)
            self.wfile.write(payload.encode("utf-8"))
        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "python_form_demo"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/submit":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Endpoint Not Found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 65536:  # 64 KB limit
            self.send_response(413)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Payload Too Large")
            return

        body = self.rfile.read(content_length).decode("utf-8", errors="replace")
        form_dict = urllib.parse.parse_qs(body, keep_blank_values=True)

        # Extract values
        full_name = form_dict.get("full_name", [""])[0].strip()
        reg_no = form_dict.get("registration_no", [""])[0].strip()
        email = form_dict.get("email", [""])[0].strip()
        event_choice = form_dict.get("event_choice", [""])[0].strip()
        notes = form_dict.get("special_notes", [""])[0].strip()

        errors = []
        if not full_name:
            errors.append("Full Name is required.")
        elif len(full_name) < 2 or len(full_name) > 100:
            errors.append("Full Name must be between 2 and 100 characters.")

        if not reg_no:
            errors.append("Registration Number is required.")
        elif not ROLL_REGEX.match(reg_no):
            errors.append("Registration Number must be 8-10 numeric digits.")

        if not email:
            errors.append("Email address is required.")
        elif not EMAIL_REGEX.match(email):
            errors.append("Invalid email address format.")

        valid_events = [
            "MUJ Hackathon 2026",
            "Symphony Night",
            "Inter-Department Football",
            "AI & Robotics Workshop",
        ]
        if not event_choice:
            errors.append("Event selection is required.")
        elif event_choice not in valid_events:
            errors.append("Selected event is not in the approved events list.")

        if errors:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_out = render_response_page(
                success=False,
                title="The submitted form contained validation errors. Please correct them.",
                messages=errors,
            )
            self.wfile.write(html_out.encode("utf-8"))
            return

        # Registration record (safe from XSS when rendered)
        record = {
            "id": len(REGISTRATIONS_LOG) + 1,
            "full_name": full_name,
            "registration_no": reg_no,
            "email": email,
            "event_choice": event_choice,
            "special_notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        REGISTRATIONS_LOG.append(record)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html_out = render_response_page(
            success=True,
            title=f"Student {full_name} registered for '{event_choice}'.",
            messages=[
                "Server-side validation passed completely.",
                "Input sanitized and escaped against XSS attacks.",
                f"Session Record ID: #{record['id']}",
            ],
            data=record,
        )
        self.wfile.write(html_out.encode("utf-8"))

def run():
    with socketserver.TCPServer(("", PORT), FormHandler) as httpd:
        print(f"MUJVERSE Python Form Processing Demo running at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    run()
