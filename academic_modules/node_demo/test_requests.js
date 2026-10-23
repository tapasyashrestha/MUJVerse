/**
 * MUJVERSE Node.js Demo — Verification Script
 * ============================================
 * Run: node test_requests.js
 * Requires the server to be running on http://localhost:3000
 * (start with: npm start  in a separate terminal)
 */

"use strict";

const BASE = "http://localhost:3000";
let passed = 0;
let failed = 0;

async function request(path) {
  const url = `${BASE}${path}`;
  const res = await fetch(url);
  const body = await res.json();
  return { status: res.status, body };
}

function assert(label, condition, detail = "") {
  if (condition) {
    console.log(`  ✅ PASS: ${label}`);
    passed++;
  } else {
    console.error(`  ❌ FAIL: ${label}${detail ? " — " + detail : ""}`);
    failed++;
  }
}

async function run() {
  console.log("MUJVERSE Node.js Demo — API Verification\n");

  // ── /api/health ─────────────────────────────────────────────────────────
  console.log("1. GET /api/health");
  const health = await request("/api/health");
  assert("status 200", health.status === 200);
  assert("status: ok", health.body.status === "ok");
  assert("has uptime_seconds", typeof health.body.uptime_seconds === "number");

  // ── /api/events (default) ───────────────────────────────────────────────
  console.log("\n2. GET /api/events");
  const events = await request("/api/events");
  assert("status 200", events.status === 200);
  assert("success: true", events.body.success === true);
  assert("returns array", Array.isArray(events.body.events));
  assert("total is 5", events.body.total === 5);
  assert("has pagination keys", "page" in events.body && "totalPages" in events.body);

  // ── /api/events?category=technical ──────────────────────────────────────
  console.log("\n3. GET /api/events?category=technical");
  const cat = await request("/api/events?category=technical");
  assert("status 200", cat.status === 200);
  assert("filtered to 1 result", cat.body.total === 1);
  assert("correct title", cat.body.events[0].title === "MUJ Hackathon 2026");

  // ── /api/events?q=cricket ───────────────────────────────────────────────
  console.log("\n4. GET /api/events?q=cricket");
  const search = await request("/api/events?q=cricket");
  assert("status 200", search.status === 200);
  assert("filtered to 1", search.body.total === 1);

  // ── /api/events?available=true ──────────────────────────────────────────
  console.log("\n5. GET /api/events?available=true");
  const avail = await request("/api/events?available=true");
  assert("status 200", avail.status === 200);
  assert("excludes full events", avail.body.events.every((e) => e.registered < e.capacity));
  assert("cricket (full) excluded", !avail.body.events.some((e) => e.title.includes("Cricket")));

  // ── /api/events/:id (valid) ──────────────────────────────────────────────
  console.log("\n6. GET /api/events/1");
  const single = await request("/api/events/1");
  assert("status 200", single.status === 200);
  assert("correct event", single.body.event.id === 1);
  assert("has available_seats", typeof single.body.event.available_seats === "number");
  assert("has is_full", typeof single.body.event.is_full === "boolean");

  // ── /api/events/:id (not found) ─────────────────────────────────────────
  console.log("\n7. GET /api/events/9999");
  const notFound = await request("/api/events/9999");
  assert("status 404", notFound.status === 404);
  assert("success: false", notFound.body.success === false);
  assert("has error message", typeof notFound.body.error === "string");

  // ── /api/events/:id (invalid — string) ──────────────────────────────────
  console.log("\n8. GET /api/events/abc");
  const invalid = await request("/api/events/abc");
  assert("status 400", invalid.status === 400);
  assert("success: false", invalid.body.success === false);

  // ── /api/categories ─────────────────────────────────────────────────────
  console.log("\n9. GET /api/categories");
  const cats = await request("/api/categories");
  assert("status 200", cats.status === 200);
  assert("returns 5 categories", cats.body.categories.length === 5);

  // ── 404 route ───────────────────────────────────────────────────────────
  console.log("\n10. GET /api/nonexistent");
  const miss = await request("/api/nonexistent");
  assert("status 404", miss.status === 404);
  assert("lists available routes", Array.isArray(miss.body.available_routes));

  // ── Summary ─────────────────────────────────────────────────────────────
  console.log(`\n${"─".repeat(50)}`);
  console.log(`Results: ${passed} passed, ${failed} failed`);
  if (failed > 0) process.exit(1);
}

run().catch((err) => {
  console.error("\nCould not connect to server. Is it running?");
  console.error("Start it with: npm start");
  console.error(err.message);
  process.exit(1);
});
