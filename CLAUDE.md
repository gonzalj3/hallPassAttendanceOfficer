# Hall Pass Attendance Officer (HPAO)

Hackathon MVP. **Single school.** Backend + agent that owns attendance, hall passes, and policy compliance, and emits real-time alerts.

## Status (2026-05-09)

| Area | State |
|---|---|
| Persistence: schools, students, users, classes, sessions, attendance, hall passes, alerts, agent_messages | ✅ migrations 0001–0008 |
| Attendance service (`record_attendance`, `list_*`) — idempotent upsert | ✅ |
| Hall pass service (issue/check-in/overdue) + 15-min restroom default | ✅ |
| Real-time `LISTEN/NOTIFY` + WebSocket fan-out (other agent) | ✅ |
| Policy ingestion + pgvector RAG + rule evaluator (other agent) | ✅ |
| Alerts service + `detect_overdue_passes` (the headline trigger) | ✅ |
| Inter-agent boundary endpoints (HMAC-signed) | ✅ except `policy-search` + `excuses` (not yet exposed) |
| Demo dispatcher loop (`detect → dispatch`) + CLI runner | ✅ |
| OpenAI Codex agent loop wrapping the tool surface | ⏭ optional, post-demo |
| Audit log + observability hardening | ⏭ optional, post-hackathon |

Test gate: ~258 tests on `main`, full suite green. Pre-commit runs unit on commit, full suite on push.

## Quick start

```bash
git clone <repo> && cd hallPassAttendanceOfficer
make install          # python3 -m venv .venv && pip install -e ".[dev]" && pre-commit install
make db-up            # docker compose up -d db (Postgres 16 + pgvector)
.venv/bin/alembic upgrade head
make test             # full suite (Docker required for integration)
```

Make targets: `install` · `test` · `test-unit` · `test-integration` · `lint` · `fmt` · `type` · `db-up` · `db-down` · `hooks` · `clean`.

Required env (or `.env`):

| Var | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | — | `postgresql+asyncpg://hpao:hpao@localhost:5432/hpao` for local |
| `APP_ENV` | no | `dev` | |
| `PARENT_COMMS_URL` | for outbound webhooks | unset | Base URL of the teammate's parent-comms agent |
| `PARENT_COMMS_SECRET` | for outbound webhooks | unset | Shared HMAC secret; must match parent-comms config |
| `DISPATCHER_INTERVAL_SECONDS` | no | `30.0` | Drop to `5` for live demo |
| `OPENAI_API_KEY` | for policy ingestion + agent loop | unset | Used by Phase 5c embeddings and the planned Phase 7 agent. Tests stub it out. |
| `OPENAI_PROJECT_ID` | no | unset | Optional — pins API calls to a specific OpenAI project |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | Default chat model for the agent loop |
| `OPENAI_EMBEDDING_MODEL` | no | `text-embedding-3-small` | Used by Phase 5c policy chunk embedding |
| `FRONTEND_ORIGIN` | no | the deployed Netlify URL | CORS allow-list for the API. Comma-separate multiple origins. `http://localhost:*` is always allowed for dev. |

If `PARENT_COMMS_URL` / `_SECRET` are unset, the dispatcher still runs `detect_overdue_passes` (state hygiene) but skips outbound webhooks — useful when the teammate's agent isn't up.

## Run the API locally (for the frontend)

```bash
make db-up                                   # Postgres 16 + pgvector
.venv/bin/alembic upgrade head               # schema
.venv/bin/uvicorn --factory hpao.app:app_factory --reload --port 8000
```

The app exposes:
- `GET  /healthz`                       — liveness
- `GET  /openapi.json` · `/docs`        — Swagger UI
- `WS   /v1/realtime?channel=…`         — Phase 4c fan-out
- `POST /v1/agent/inbound/parent-message` (HMAC) — Phase 8 inter-agent
- `POST /v1/agent/inbound/parent-response` (HMAC)
- `GET  /v1/agent/student-context/{id}` (HMAC)

CORS: `FRONTEND_ORIGIN` (defaults to the deployed Netlify URL) plus any `http://localhost:*` are allowed for browsers.

## Demo runbook (the 15-min restroom flow, end-to-end)

Two terminals.

**Terminal 1 — dispatcher loop:**
```bash
DATABASE_URL=postgresql+asyncpg://hpao:hpao@localhost:5432/hpao \
PARENT_COMMS_URL=https://your-teammate-agent.example \
PARENT_COMMS_SECRET=shared-hmac-secret \
DISPATCHER_INTERVAL_SECONDS=5 \
  python -m hpao.cli.dispatcher
```

CLI flags: `--once` (single cycle, prints summary, exits) · `--interval N` (override loop interval).

**Terminal 2 — issue a hall pass that will trip the alert:**
```python
# in a python REPL or seed script
from hpao.services.hall_pass import issue_pass
await issue_pass(
    db,
    student_id=student.id,
    originating_class_session_id=session.id,
    destination="RESTROOM",
    issued_by=teacher.id,
    duration_minutes=1,  # 1 min for fast demo (default is 15)
)
```

Within `DISPATCHER_INTERVAL_SECONDS` of the pass going overdue, Terminal 1 logs the alert raised + webhook fired. The `agent_messages` table will have `direction=OUTBOUND`, `status=SENT`, `alert_id=<the alert>`.

The signed payload that lands at the teammate's `/notifications`:

```json
{
  "correlation_id": "uuid",
  "event": "alert.raised",
  "severity": "high",
  "student_id": "uuid",
  "guardians": [],
  "context": {
    "rule_key": "hallpass.restroom.duration_exceeded",
    "summary": "Student out of class 17 min (restroom)",
    "evidence": { "hall_pass_id": "...", "destination": "RESTROOM", "minutes_elapsed": 17 }
  },
  "intent": "notify"
}
```

Header: `X-HPAO-Signature: hex(hmac_sha256(PARENT_COMMS_SECRET, raw_body))`.

### Talking to the OpenAI agent ad-hoc

For investigating student state via an LLM (Phase 7):

```bash
OPENAI_API_KEY=... \
DATABASE_URL=... \
  python -m hpao.cli.agent "How many days has student S00042 been absent this semester?"
```

The agent has tools for: `lookup_student_by_number`, `get_student_attendance`, `get_active_hall_pass`, `get_open_alerts_for_student`, `query_policy`, `record_attendance_as_agent`, `raise_alert_for_student`, `dispatch_pending_alerts`. It will call them and respond with a terse staff-facing summary.

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

### HPAO → parent-comms (outbound webhook) ✅ implemented

`POST {parent_comms_base}/notifications` — payload shape shown in **Demo runbook** above.

### parent-comms → HPAO (HPAO exposes)

| Method | Path | State |
|---|---|---|
| `POST` | `/v1/agent/inbound/parent-message` | ✅ implemented |
| `POST` | `/v1/agent/inbound/parent-response` | ✅ implemented |
| `GET`  | `/v1/agent/student-context/{student_id}?since=YYYY-MM-DD` | ✅ implemented |
| `GET`  | `/v1/agent/policy-search?q=...` | 🚧 service exists (Phase 5c), HTTP endpoint not yet exposed |
| `POST` | `/v1/agent/excuses` | 🚧 not yet implemented |

POSTs return `{accepted, agent_message_id, correlation_id, duplicate}`. Same `correlation_id` posted twice → `duplicate=true`, no double-write.

`student-context` returns `{student_id, student_number, grade_level, first_name, last_name, school_id, attendance_summary, active_hall_passes[], open_alerts[]}`.

## Real-time events

Delivered via WebSocket at `/v1/realtime?channel=...` (multi-channel subscribe) and outbound webhook (parent-comms, severity ≥ medium).

Channels: `school:{id}` · `class:{id}` · `student:{id}`.

Event types:
- `attendance.recorded`
- `hallpass.issued`
- `hallpass.returned`
- `hallpass.overdue` — fires when `now > expected_return_at` (default 15 min for restroom, configurable per destination)
- `alert.raised`

## Data model (essentials)

Every table has `id` (UUIDv4), `created_at`, `updated_at` (TIMESTAMPTZ).

| Table | Key fields | Notes |
|---|---|---|
| `schools` | `name`, `district` | |
| `students` | `school_id` FK, `student_number`, `grade_level` | UNIQUE(`school_id`, `student_number`) |
| `users` | `school_id` FK, `email`, `role`, `first_name`, `last_name` | role ∈ TEACHER/ADMIN/COUNSELOR/NURSE |
| `classes` | `school_id` FK, `teacher_id` FK, `name`, `period`, `room` | |
| `class_enrollments` | `class_id`, `student_id`, `enrolled_at` | UNIQUE(class, student) |
| `class_sessions` | `class_id` FK, `date`, `scheduled_start`, `scheduled_end` | UNIQUE(class, date) |
| `attendance_records` | `class_session_id` FK, `student_id` FK, `status`, `source`, `recorded_by`, `notes` | UNIQUE(session, student) |
| `hall_passes` | `student_id`, `originating_class_session_id`, `destination`, `checked_out_at`, `expected_return_at`, `checked_in_at`, `status`, `issued_by` | Partial UNIQUE(student) WHERE `status='ACTIVE'` |
| `policies` / `policy_chunks` / `policy_rules` | RAG corpus + structured rule expressions | pgvector embeddings on chunks |
| `alerts` | `student_id`, `rule_key`, `severity`, `status`, `context` JSONB, `acknowledged_by` | Partial UNIQUE(student, rule_key) WHERE `status='OPEN'` |
| `agent_messages` | `direction`, `counterparty`, `correlation_id`, `student_id?`, `alert_id?`, `payload` JSONB, `status` | UNIQUE(direction, correlation_id) |

`guardians` / `student_guardians` — **not built**; parent-comms owns guardian state. HPAO references guardians only as opaque IDs in payloads.

Enums:
- `attendance.status`: `PRESENT | ABSENT | TARDY | EXCUSED | UNEXCUSED`
- `attendance.source`: `TEACHER | AGENT | IMPORT`
- `hall_pass.status`: `ACTIVE | RETURNED | OVERDUE | FLAGGED`
- `hall_pass.destination`: `RESTROOM | NURSE | COUNSELOR | OFFICE | OTHER`
- `alert.severity`: `low | medium | high | critical`
- `alert.status`: `OPEN | ACKNOWLEDGED | RESOLVED`
- `agent_message.direction`: `INBOUND | OUTBOUND`
- `agent_message.status`: `PENDING | SENT | FAILED | RECEIVED`

## Policy engine (hybrid)

1. **Deterministic rules** — evaluated on relevant writes + nightly batch. Seed set:
   - `tea.compulsory_attendance.90_percent` — TEC §25.092, attend ≥ 90% of days offered.
   - `tea.truancy.unexcused_absences` — 3 unexcused in 4-week window or 10 in 6 months.
   - `pfisd.18_day_max` — alert at 15 absences (configurable threshold).
   - `hallpass.<destination>.duration_exceeded` — `hall_pass` open past `expected_return_at`. RESTROOM = severity `high`, others = `medium`.
2. **RAG** over policy docs for nuance (e.g. exemption eligibility under TEC §25.087). **Advisory only** — cannot override deterministic outcomes.

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2
- PostgreSQL 16 + pgvector; real-time via `LISTEN/NOTIFY` → WebSockets
- **Agents run on OpenAI (hackathon Codex credits)** — Agents SDK / Responses API with function calling. Not Anthropic.
- pytest (unit + integration via testcontainers + contract + e2e), ruff (lint + format), mypy
- pre-commit hooks: fast unit tests on commit; full suite on push; CI mirrors push

## Conventions

- IDs: UUIDv4 (UUIDv7 deferred — not in stdlib for our `>=3.12` floor).
- Times: UTC ISO-8601 in payloads; school-local time stored on session records.
- All POSTs accept `Idempotency-Key` header; boundary endpoints additionally key off `correlation_id`.
- Errors: RFC 7807 `application/problem+json`.
- Auth between services: HMAC-SHA256 over raw body (`X-HPAO-Signature`).

## Out of scope (hackathon)

SSO, SIS sync, multi-tenant, mobile UIs, push notifications, parent-facing UX (teammate's agent owns it), teacher dashboard UI (other coworkers).

## Pointers

- **Plan + status**: `PLAN.md` (living doc, also tracks per-phase completion).
- **Migrations**: `alembic/versions/` (0001–0008 currently).
- **Domain models**: `src/hpao/models/`.
- **Services** (DB I/O, business logic): `src/hpao/services/` — `attendance.py`, `hall_pass.py`, `alerts.py`, `agent_messages.py`, `dispatcher.py`.
- **API routers**: `src/hpao/api/agent.py` (boundary), `src/hpao/realtime/` (WebSocket).
- **Outbound HTTP client**: `src/hpao/integrations/parent_comms.py`.
- **Boundary schemas (Pydantic)**: `src/hpao/schemas/agent.py`.
- **HMAC sign/verify**: `src/hpao/api/security.py`.
- **CLI demo runner**: `python -m hpao.cli.dispatcher`.
- **OpenAPI**: `/openapi.json` once an app mounting the routers is running.
