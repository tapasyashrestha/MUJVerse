/**
 * MUJVERSE Academic Demo — Node.js + Express JSON API
 * =====================================================
 * Educational demonstration of a RESTful Express API.
 * Uses in-memory sample data only — no production DB connection.
 * Run: node server.js  (or: npm start)
 *
 * Educational concepts covered:
 *  - Express routing and middleware
 *  - Route parameters and query-string handling
 *  - Request validation and structured error responses
 *  - JSON serialisation and Content-Type headers
 *  - Pagination and basic filtering
 *  - CORS headers for browser demos
 */

"use strict";

const express = require("express");
const app = express();
const PORT = process.env.PORT || 3000;

// ── Sample data (read-only, mirrors MUJVERSE categories/events) ─────────────
const CATEGORIES = [
  { id: 1, name: "Technical", icon: "bi-cpu" },
  { id: 2, name: "Cultural & Arts", icon: "bi-palette" },
  { id: 3, name: "Sports", icon: "bi-trophy" },
  { id: 4, name: "Workshop", icon: "bi-tools" },
  { id: 5, name: "E-Summit", icon: "bi-graph-up" },
];

const EVENTS = [
  {
    id: 1,
    title: "MUJ Hackathon 2026",
    category_id: 1,
    category: "Technical",
    venue: "Innovation Lab, Block A",
    start_datetime: "2026-11-15T09:00:00+05:30",
    end_datetime: "2026-11-16T18:00:00+05:30",
    registration_deadline: "2026-11-10T23:59:00+05:30",
    capacity: 200,
    registered: 147,
    status: "approved",
    organizer: "Tech Club MUJ",
    description:
      "24-hour hackathon open to all students. Build innovative solutions for real-world campus problems. Prizes worth ₹1,00,000.",
  },
  {
    id: 2,
    title: "Symphony Night",
    category_id: 2,
    category: "Cultural & Arts",
    venue: "Open Air Amphitheatre",
    start_datetime: "2026-11-20T18:30:00+05:30",
    end_datetime: "2026-11-20T22:00:00+05:30",
    registration_deadline: "2026-11-18T23:59:00+05:30",
    capacity: 500,
    registered: 312,
    status: "approved",
    organizer: "Crescendo — MUJ Music Society",
    description:
      "Annual inter-college band competition with performances from 12 bands across Rajasthan.",
  },
  {
    id: 3,
    title: "Inter-College Cricket League",
    category_id: 3,
    category: "Sports",
    venue: "Main Cricket Ground",
    start_datetime: "2026-12-01T08:00:00+05:30",
    end_datetime: "2026-12-05T18:00:00+05:30",
    registration_deadline: "2026-11-25T23:59:00+05:30",
    capacity: 300,
    registered: 300,
    status: "approved",
    organizer: "Sports Council MUJ",
    description:
      "5-day T20 cricket tournament. Teams of 11 players. Registration closed — capacity reached.",
  },
  {
    id: 4,
    title: "AI/ML Workshop",
    category_id: 4,
    category: "Workshop",
    venue: "Computer Science Lab 3, Block C",
    start_datetime: "2026-11-28T10:00:00+05:30",
    end_datetime: "2026-11-28T16:00:00+05:30",
    registration_deadline: "2026-11-25T18:00:00+05:30",
    capacity: 60,
    registered: 41,
    status: "approved",
    organizer: "IEEE MUJ Student Chapter",
    description:
      "Hands-on workshop covering Python, scikit-learn, and neural networks. Bring your laptop.",
  },
  {
    id: 5,
    title: "E-Summit 2026",
    category_id: 5,
    category: "E-Summit",
    venue: "Seminar Hall, Admin Block",
    start_datetime: "2026-12-10T09:00:00+05:30",
    end_datetime: "2026-12-11T18:00:00+05:30",
    registration_deadline: "2026-12-05T23:59:00+05:30",
    capacity: 400,
    registered: 88,
    status: "approved",
    organizer: "E-Cell MUJ",
    description:
      "Annual entrepreneurship summit with keynote speakers, startup pitches, and investor panels.",
  },
];

// ── Middleware ───────────────────────────────────────────────────────────────
app.use(express.json());

// Simple CORS headers for local browser demos
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.sendStatus(204);
  next();
});

// Request logger
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

// ── Helper: paginate an array ────────────────────────────────────────────────
function paginate(array, page, limit) {
  const p = Math.max(1, parseInt(page) || 1);
  const l = Math.min(50, Math.max(1, parseInt(limit) || 10));
  const total = array.length;
  const totalPages = Math.ceil(total / l);
  const data = array.slice((p - 1) * l, p * l);
  return { data, total, page: p, limit: l, totalPages };
}

// ── Routes ───────────────────────────────────────────────────────────────────

/**
 * GET /api/health
 * Simple liveness check — always returns 200 with server info.
 */
app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    service: "MUJVERSE Academic Node.js Demo",
    version: "1.0.0",
    node: process.version,
    uptime_seconds: Math.floor(process.uptime()),
    timestamp: new Date().toISOString(),
  });
});

/**
 * GET /api/events
 * Returns paginated list of events.
 *
 * Query parameters:
 *   page      (int, default 1)
 *   limit     (int, default 10, max 50)
 *   category  (string, partial match, case-insensitive)
 *   q         (string, search title or description)
 *   available (boolean: "true" filters to events with remaining capacity)
 */
app.get("/api/events", (req, res) => {
  let results = [...EVENTS];

  // Filter: category name (partial, case-insensitive)
  if (req.query.category) {
    const cat = req.query.category.toLowerCase();
    results = results.filter((e) => e.category.toLowerCase().includes(cat));
  }

  // Filter: full-text search on title + description
  if (req.query.q) {
    const q = req.query.q.toLowerCase();
    results = results.filter(
      (e) =>
        e.title.toLowerCase().includes(q) ||
        e.description.toLowerCase().includes(q)
    );
  }

  // Filter: only events with available capacity
  if (req.query.available === "true") {
    results = results.filter((e) => e.registered < e.capacity);
  }

  const { data, total, page, limit, totalPages } = paginate(
    results,
    req.query.page,
    req.query.limit
  );

  res.json({
    success: true,
    total,
    page,
    limit,
    totalPages,
    events: data,
  });
});

/**
 * GET /api/events/:id
 * Returns a single event by numeric ID.
 * Validates that :id is a positive integer.
 */
app.get("/api/events/:id", (req, res) => {
  const id = parseInt(req.params.id, 10);

  // Parameter validation
  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({
      success: false,
      error: "Invalid event ID. Must be a positive integer.",
      received: req.params.id,
    });
  }

  const event = EVENTS.find((e) => e.id === id);

  if (!event) {
    return res.status(404).json({
      success: false,
      error: `Event with id ${id} not found.`,
    });
  }

  res.json({
    success: true,
    event: {
      ...event,
      available_seats: event.capacity - event.registered,
      is_full: event.registered >= event.capacity,
    },
  });
});

/**
 * GET /api/categories
 * Returns all categories.
 */
app.get("/api/categories", (req, res) => {
  res.json({ success: true, categories: CATEGORIES });
});

// ── 404 handler ──────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: "Route not found.",
    available_routes: [
      "GET /api/health",
      "GET /api/categories",
      "GET /api/events?page=1&limit=10&category=&q=&available=true",
      "GET /api/events/:id",
    ],
  });
});

// ── Global error handler ─────────────────────────────────────────────────────
app.use((err, req, res, _next) => {
  console.error("Unhandled error:", err);
  res.status(500).json({
    success: false,
    error: "Internal server error.",
  });
});

// ── Start server ─────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`MUJVERSE Node.js Demo API running at http://localhost:${PORT}`);
  console.log("Available routes:");
  console.log(`  GET http://localhost:${PORT}/api/health`);
  console.log(`  GET http://localhost:${PORT}/api/categories`);
  console.log(`  GET http://localhost:${PORT}/api/events`);
  console.log(`  GET http://localhost:${PORT}/api/events/:id`);
  console.log("\nPress Ctrl+C to stop.");
});

module.exports = app; // export for testing
