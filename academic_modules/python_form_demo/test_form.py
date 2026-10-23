"""
Verification script for Python Form Processing Demo
==================================================
Sends simulated GET and POST requests (valid and invalid) to test validation and sanitization.
"""

import http.client
import json
import urllib.parse

HOST = "127.0.0.1"
PORT = 8050

def run_tests():
    conn = http.client.HTTPConnection(HOST, PORT, timeout=5)

    print("=== Testing Python Form Processing Demo ===")

    # Test 1: GET /health
    conn.request("GET", "/health")
    res = conn.getresponse()
    body = res.read().decode()
    assert res.status == 200, f"Health check failed: {res.status}"
    data = json.loads(body)
    print(f"1. GET /health -> Status {res.status}, Service: {data.get('service')} [PASS]")

    # Test 2: GET / (Form Page)
    conn.request("GET", "/")
    res = conn.getresponse()
    body = res.read().decode()
    assert res.status == 200, f"GET / failed: {res.status}"
    assert "Event Registration Form" in body
    print(f"2. GET / (Form HTML) -> Status {res.status}, contains form element [PASS]")

    # Test 3: POST /submit (Valid payload)
    valid_payload = urllib.parse.urlencode({
        "full_name": "Aarav Gupta",
        "registration_no": "210905999",
        "email": "aarav.gupta@muj.manipal.edu",
        "event_choice": "MUJ Hackathon 2026",
        "special_notes": "Needs vegan meal"
    })
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    conn.request("POST", "/submit", body=valid_payload, headers=headers)
    res = conn.getresponse()
    body = res.read().decode()
    assert res.status == 200, f"Valid POST failed: {res.status}"
    assert "Registration Successful!" in body
    print(f"3. POST /submit (Valid) -> Status {res.status}, Successful submission [PASS]")

    # Test 4: POST /submit (Invalid payload - missing email & bad roll number)
    invalid_payload = urllib.parse.urlencode({
        "full_name": "Bad Data",
        "registration_no": "123", # Too short
        "email": "not-an-email",
        "event_choice": "Non-existent Event"
    })
    conn.request("POST", "/submit", body=invalid_payload, headers=headers)
    res = conn.getresponse()
    body = res.read().decode()
    assert res.status == 400, f"Invalid POST should return 400, got: {res.status}"
    assert "Validation Failed" in body
    assert "Registration Number must be 8-10 numeric digits" in body
    print(f"4. POST /submit (Invalid) -> Status {res.status}, Correctly rejected with errors [PASS]")

    # Test 5: POST /submit (XSS payload sanitization)
    xss_payload = urllib.parse.urlencode({
        "full_name": "<script>alert('xss')</script>",
        "registration_no": "210905888",
        "email": "hacker@muj.edu",
        "event_choice": "Symphony Night",
        "special_notes": "<img src=x onerror=alert(1)>"
    })
    conn.request("POST", "/submit", body=xss_payload, headers=headers)
    res = conn.getresponse()
    body = res.read().decode()
    assert res.status == 200
    assert "<script>" not in body, "XSS script tag was not escaped!"
    assert "&lt;script&gt;" in body, "XSS script tag should be HTML-escaped!"
    print(f"5. POST /submit (XSS Sanitization) -> Status {res.status}, Script tags safely escaped [PASS]")

    print("\nAll Python Form Processing verification tests PASSED!\n")

if __name__ == "__main__":
    run_tests()
