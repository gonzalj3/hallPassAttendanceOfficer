# Hall Pass Attendance Officer (HPAO)

Hackathon MVP. **Single school.** Backend + agent that owns attendance, hall passes, and policy compliance, and emits real-time alerts.

## What HPAO is (and isn't)

- **Owns**: schools, classes, students, teachers, attendance, hall passes, policy rules, alerts, agent-message log.
- **Does**: records attendance, tracks hall-pass check-out/check-in, evaluates deterministic policy rules, raises real-time alerts (e.g. restroom > 15 min → on-duty admin).
- **Is not**: parent communications, dashboard UIs, SSO/identity, SIS sync.

## Directionality

HPAO sits on the **agent boundary** (HTTPS between services), not the **parent boundary** (SMS/email/phone). It is bidirectional on the agent boundary but **receive-only** at the parent boundary — HPAO never originates a parent-facing message and ships no Twilio/SMTP/phone client.

- HPAO emits **structured intents** (`rule_key`, `severity`, `evidence`, `intent` enum), never message bodies.
- The parent-comms agent owns wording, language, channel selection, opt-outs, quiet hours.
- `agent_messages` is a log of intents and decisions — actual SMS/email transcripts live in parent-comms.
- Tests assert webhook payload shape, not message content; HPAO authors no parent-facing copy.

## Boundary with the parent-comms agent (teammate)

The parent-comms agent **initiates and receives** all parent/admin conversations. HPAO never contacts parents directly. All boundary calls are HMAC-signed (`X-HPAO-Signature: hex(hmac_sha256(secret, body))`) and idempotent on `correlation_id`.

### HPAO → parent-comms (outbound webhook)

`POST {parent_comms_base}/notifications`

```json
{
  "correlation_id": "uuid",
  "event": "alert.raised",
  "severity": "low|medium|high|critical",
  "student_id": "uuid",
  "guardians": [
    {"id": "uuid", "name": "...", "preferred_channel": "sms|email|call", "preferred_language": "en|es"}
  ],
  "context": {
    "rule_key": "restroom.duration_exceeded",
    "summary": "Student out of class 17 minutes",
    "evidence": { "hall_pass_id": "...", "checked_out_at": "...", "minutes_elapsed": 17 }
  },
  "intent": "notify|request_info|request_exemption_review"
}
```

### parent-comms → HPAO (HPAO exposes)

- `POST /v1/agent/inbound/parent-message` — log parent-initiated contact, attach to a student.
- `POST /v1/agent/inbound/parent-response` — relay a parent reply (excuse note, exemption claim) so HPAO can update attendance/alerts.
- `GET  /v1/agent/student-context/{student_id}` — attendance summary, active alerts, recent hall passes, applicable rules. Use for grounding replies.
- `GET  /v1/agent/policy-search?q=...` — RAG over ingested policy docs (TEA, district, school). Use this rather than reasoning over policy yourself.
- `POST /v1/agent/excuses` — submit an excused-absence claim with supporting note; HPAO decides per deterministic rule.

## Real-time events

Delivered via WebSocket (dashboards) and outbound webhook (parent-comms, severity ≥ medium).

Channels: `school:{id}` · `class:{id}` · `student:{id}`

Event types:
- `attendance.recorded`
- `hallpass.issued`
- `hallpass.returned`
- `hallpass.overdue` — fires when `now > expected_return_at` (default 15 min for restroom, configurable per destination)
- `alert.raised`

## Data model (essentials)

Every table has `id` (UUIDv7), `created_at`, `updated_at`. State changes append to `audit_log`.

| Table | Key fields |
|---|---|
| `students` | `student_number`, `grade_level` |
| `guardians` | `name`, `phone`, `email`, `preferred_language`, `preferred_channel` |
| `student_guardians` | M2M with `relationship`, `is_primary` |
| `teachers` / `users` | `email`, `role`, `name` |
| `classes` | `teacher_id`, `name`, `period`, `room` |
| `class_sessions` | `class_id`, `date`, `scheduled_start`, `scheduled_end` |
| `attendance_records` | `class_session_id`, `student_id`, `status`, `source`, `recorded_by`, `notes` |
| `hall_passes` | `student_id`, `originating_class_session_id`, `destination`, `reason`, `checked_out_at`, `expected_return_at`, `checked_in_at`, `status`, `issued_by` |
| `policies` | `scope`, `name`, `source_url`, `version`, `effective_date` |
| `policy_chunks` | `policy_id`, `text`, `embedding` (pgvector) |
| `policy_rules` | `policy_id`, `rule_key`, `expression` (JSONB), `threshold`, `severity` |
| `alerts` | `student_id`, `rule_key`, `severity`, `status`, `acknowledged_by` |
| `agent_messages` | `direction`, `counterparty`, `student_id`, `payload` (JSONB), `correlation_id`, `status` |

Hard invariants (DB-enforced):
- One `ACTIVE` hall_pass per student at a time.
- One `attendance_record` per (`class_session_id`, `student_id`).

Enums:
- `attendance.status`: `PRESENT | ABSENT | TARDY | EXCUSED | UNEXCUSED`
- `hall_pass.status`: `ACTIVE | RETURNED | OVERDUE | FLAGGED`
- `hall_pass.destination`: `RESTROOM | NURSE | COUNSELOR | OFFICE | OTHER`
- `alert.severity`: `low | medium | high | critical`

## Policy engine (hybrid)

1. **Deterministic rules** — evaluated on relevant writes + nightly batch. Seed set:
   - `tea.compulsory_attendance.90_percent` — TEC §25.092, attend ≥ 90% of days offered.
   - `tea.truancy.unexcused_absences` — 3 unexcused in 4-week window or 10 in 6 months.
   - `pfisd.18_day_max` — alert at 15 absences (configurable threshold).
   - `restroom.duration_exceeded` — `hall_pass` open past `expected_return_at`.
2. **RAG** over policy docs for nuance (e.g. exemption eligibility under TEC §25.087). **Advisory only** — cannot override deterministic outcomes.

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2
- PostgreSQL 16 + pgvector; real-time via `LISTEN/NOTIFY` → WebSockets
- **Agents run on OpenAI (hackathon Codex credits)** — Agents SDK / Responses API with function calling. Not Anthropic.
- pytest (unit + integration via testcontainers + contract + e2e), ruff (lint + format), mypy
- pre-commit hooks: fast unit tests on commit; full suite on push; CI mirrors push

## Conventions

- IDs: UUIDv7 (sortable).
- Times: UTC ISO-8601 in payloads; school-local time stored on session records.
- All POSTs accept `Idempotency-Key` header.
- Errors: RFC 7807 `application/problem+json`.
- Auth between services: HMAC-SHA256 over raw body.

## Out of scope (hackathon)

SSO, SIS sync, multi-tenant, mobile UIs, push notifications, parent-facing UX (teammate's agent owns it), teacher dashboard UI (other coworkers).

## Pointers

- OpenAPI: `/openapi.json` (once running).
- Migrations: `alembic/versions/`.
- Rule definitions: `src/hpao/policy/rules/`.
- Boundary schemas: `src/hpao/schemas/agent.py`.
