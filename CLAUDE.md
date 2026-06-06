# Monitor Lizzie

Digital hall-pass tracker for K-12. Two views — teacher iPad + principal dashboard — backed by FastAPI and Postgres, deployed on Railway + Netlify. **Demo data only.** No real student PII.

## What this is

A deterministic monitor for one specific question: *who is out of class and how long have they been gone?* Teachers issue digital passes from an iPad UI; a backend dispatcher detects overdue passes against a per-destination duration rule (15 min restroom default) and raises an alert; the principal dashboard renders alerts in real time over WebSocket.

No LLM is called anywhere in the request path. No phone calls, no parent comms agent, no policy RAG. Those were in the hackathon version and were deliberately removed in the MVP scope-down (see `legacy/voice-agent` and `legacy/parent-comms-integration` branches if you need them).

## Quick start

```bash
git clone <repo> && cd hallPassAttendanceOfficer
make install                                    # .venv + pip install -e ".[dev]" + pre-commit
docker compose up -d db                         # Postgres 16 on :5432 (override to :5433 if collision)
.venv/bin/alembic upgrade head                  # chain: 0001 → 0002 → 0004 → 0007 → 0009 → 0010
.venv/bin/python -m lizzie.cli.seed             # Lincoln High + Ms. Rivera + Dr. Chen + 12 students
.venv/bin/uvicorn --factory lizzie.app:app_factory --reload --port 8000

# in another terminal — teacher iPad app
cd frontend && npm install && npm run dev       # Vite on :3000

# and another — principal dashboard
cd frontend-dashboard && npm install && npm run dev    # Vite on :3100
```

Visit the iPad app at `http://localhost:3000/`, click the **Teacher** button → you're signed in as Ms. Rivera. The dashboard at `http://localhost:3100/` clicks **Principal** → signed in as Dr. Chen.

## Required env

| Var | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | — | `postgresql+asyncpg://lizzie:lizzie@localhost:5432/lizzie` for local |
| `APP_ENV` | no | `dev` | Set to `prod` so the session cookie picks up `Secure` + `SameSite=None` |
| `SESSION_COOKIE_SECRET` | recommended | per-process random | Stable random ≥32 bytes; cookies survive a redeploy when set |
| `DISPATCHER_INTERVAL_SECONDS` | no | `30.0` | Drop to `5` for a live demo |
| `FRONTEND_ORIGIN` | no | the deployed Netlify URL | CORS allow-list. Comma-separate. `http://localhost:*` is always allowed via regex. |

Frontend (Vite, baked at build time):

| Var | Default | Notes |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8731` (teacher app) / `http://localhost:8000` (dashboard) | REST + WS base |

## API surface

| Method | Path | Auth | Notes |
|---|---|---|---|
| `GET` | `/healthz` | none | Liveness |
| `GET` | `/openapi.json`, `/docs` | none | Swagger |
| `POST` | `/auth/role-pick` | none | Body: `{"role":"TEACHER"\|"ADMIN"}`. Sets `lizzie_session` cookie. |
| `GET` | `/auth/me` | cookie | Current user, or 401 |
| `POST` | `/auth/logout` | cookie | Clears cookie |
| `GET` | `/api/sessions` | none | Today's class sessions |
| `GET` | `/api/sessions/{id}/students` | none | Roster + active passes |
| `POST` | `/api/hall-passes` | **TEACHER** | Issue. Writes `audit_log` row. |
| `POST` | `/api/hall-passes/{id}/return` | **TEACHER** | Check-in. Writes `audit_log` row. |
| `GET` | `/api/hall-passes` | none | List, optional `status_filter` / `session_id` |
| `GET` | `/api/students/lookup` | none | First+last → student record |
| `GET` | `/api/alerts` | none | Open / acknowledged / resolved |
| `DELETE` | `/api/admin/students/{id}` | **ADMIN** | Cascade delete + audit row. Built for TEC §32.155 deletion-on-request. |
| `WS` | `/v1/realtime?channel=…` | none | Multi-channel subscribe |

Read endpoints aren't gated yet — only mutations and `/admin/*` require a session. The role-picker landing page is the UI-level gate.

## Real-time events

WebSocket fan-out over `/v1/realtime?channel=…`. Channels: `school:{id}` · `class:{id}` · `student:{id}`.

Event types: `hallpass.issued` · `hallpass.returned` · `hallpass.overdue` · `alert.raised`.

## Data model

Every table has `id` (UUIDv4), `created_at`, `updated_at` (TIMESTAMPTZ) unless noted.

| Table | Key fields | Notes |
|---|---|---|
| `schools` | `name`, `district` | |
| `students` | `school_id` FK, `student_number`, `grade_level` | UNIQUE(`school_id`, `student_number`) |
| `users` | `school_id` FK, `email`, `role`, `first_name`, `last_name`, `last_sign_in_at` | role ∈ TEACHER/ADMIN/COUNSELOR/NURSE |
| `classes` | `school_id` FK, `teacher_id` FK, `name`, `period`, `room` | |
| `class_enrollments` | `class_id`, `student_id`, `enrolled_at` | UNIQUE(class, student) |
| `class_sessions` | `class_id` FK, `date`, `scheduled_start`, `scheduled_end` | UNIQUE(class, date) |
| `hall_passes` | `student_id`, `originating_class_session_id`, `destination`, `checked_out_at`, `expected_return_at`, `checked_in_at`, `status`, `issued_by` | Partial UNIQUE(student) WHERE `status='ACTIVE'` |
| `alerts` | `student_id`, `rule_key`, `severity`, `status`, `context` JSONB, `acknowledged_by` | Partial UNIQUE(student, rule_key) WHERE `status='OPEN'` |
| `audit_log` | `user_id`, `actor_role`, `action`, `target_type`, `target_id?`, `context` JSONB, `occurred_at` | Append-only. FK on `user_id` ON DELETE SET NULL so audit records outlive a deleted user. |

Enums:
- `hall_pass.status`: `ACTIVE | RETURNED | OVERDUE | FLAGGED`
- `hall_pass.destination`: `RESTROOM | NURSE | COUNSELOR | OFFICE | OTHER | HALLWAY | CLASSROOM`
- `alert.severity`: `low | medium | high | critical`
- `alert.status`: `OPEN | ACKNOWLEDGED | RESOLVED`

## Auth model (demo)

Two seeded identities (`Ms. Rivera` / `Dr. Chen`) created by `python -m lizzie.cli.seed`. The login screen on each frontend posts `{role: "TEACHER" \| "ADMIN"}` to `/auth/role-pick`; the backend resolves to the first user with that role, sets an HMAC-signed cookie, and downstream `current_user` / `require_role("ADMIN")` dependencies read the cookie.

No password store. No Google SSO. When you pilot with a real district, swap the `current_user` function in `src/lizzie/auth/dependencies.py` for one that validates a Google OIDC ID token — every router stays the same.

## Audit logging

Every hall-pass mutation and every admin action writes an `audit_log` row through `lizzie.services.audit.write_audit`. The schema is deliberately FERPA-shaped (`actor_role`, `action`, `target_type`, `target_id`, `context` JSONB) so a future pilot can start requiring rows on read paths too without changing the schema.

## Demo runbook (overdue restroom alert, end-to-end)

```bash
# Terminal 1 — dispatcher loop
DATABASE_URL=postgresql+asyncpg://lizzie:lizzie@localhost:5432/lizzie \
DISPATCHER_INTERVAL_SECONDS=5 \
  python -m lizzie.cli.dispatcher
```

```bash
# Terminal 2 — issue a 1-min pass via the iPad app or REPL
from lizzie.services.hall_pass import issue_pass
await issue_pass(
    db,
    student_id=student.id,
    originating_class_session_id=session.id,
    destination="RESTROOM",
    issued_by=teacher.id,
    duration_minutes=1,                              # tripped within ~1 min
)
```

Within `DISPATCHER_INTERVAL_SECONDS` of the pass going overdue, Terminal 1 logs the alert raised. The dashboard's WebSocket subscription receives `alert.raised` and the alert appears in the Live Activity panel.

## Local port collisions

If the host has Postgres on 5432 already, the gitignored `docker-compose.override.yml` remaps to 5433:

```yaml
services:
  db:
    ports:
      - "5433:5432"
```

```bash
DATABASE_URL=postgresql+asyncpg://lizzie:lizzie@localhost:5433/lizzie
```

Same idea for the API port — pass `--port 8765` (or whatever's free) and set `VITE_API_URL=http://localhost:8765` in `frontend/.env.local`.

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2
- PostgreSQL 16 (plain, no pgvector); real-time via `LISTEN/NOTIFY` → WebSockets
- React 18 + Vite for both frontends; Tailwind; React Router on the teacher app
- pytest (unit + integration via testcontainers), ruff (lint + format), mypy strict
- pre-commit: unit on commit, full suite on push

## Conventions

- IDs: UUIDv4
- Times: UTC ISO-8601 in payloads; school-local times stored on session records
- Errors: FastAPI default JSON envelope
- Auth: HMAC-signed cookie (`lizzie_session`), `SameSite=None;Secure` in prod, `Lax` in dev
- Cookie secret: `SESSION_COOKIE_SECRET`. Unset = per-process random (dev only)

## Pointers

- **Top-level app factory**: `src/lizzie/app.py` — `make_app(database_url, session_secret=..., is_production=...)` and `app_factory()` for `uvicorn --factory`
- **Domain models**: `src/lizzie/models/`
- **Services**: `src/lizzie/services/` — `hall_pass.py`, `alerts.py`, `audit.py`, `dispatcher.py`
- **API routers**: `src/lizzie/api/frontend.py` (browser REST), `src/lizzie/api/admin.py` (DELETE student), `src/lizzie/realtime/websocket.py` (WS)
- **Auth**: `src/lizzie/auth/` — `session.py` (sign/verify), `dependencies.py` (`current_user`, `require_role`), `router.py` (`/auth/*`)
- **Frontends**: `frontend/` (teacher iPad), `frontend-dashboard/` (principal). Each has its own `netlify.toml` + Tailwind config.
- **CLIs**:
  - `python -m lizzie.cli.dispatcher` — periodic overdue-pass detector
  - `python -m lizzie.cli.seed` — Lincoln High + Ms. Rivera + Dr. Chen + 12 students (idempotent)
- **OpenAPI**: `/openapi.json` and `/docs` once the app is running

## Out of scope

Real student PII, multi-tenant, SSO, SIS sync, mobile native apps, parent communications, AI/LLM features, voice/phone integration. None of those land in the MVP. The architecture (role-picker behind `current_user`, audit-log column shape) is deliberately built so the pilot upgrade for any of them is a config switch, not a rewrite.
