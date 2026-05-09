# HPAO Implementation Plan

Living doc. Update after each phase ships.

## Status

- ✅ **Phase 0** — TDD harness + bootstrap (pushed)
- ✅ **Phase 1** — Domain models (complete)
  - ✅ 1a: Persistence scaffolding (`d493122`)
  - ✅ 1b: Schools + Students (`110d7d0`)
  - ✅ 1c: Users + Classes + Enrollments + Class Sessions
- ✅ **Phase 2** — Attendance core (complete)
- ✅ **Phase 3** — Hall passes (complete)
- ✅ **Phase 4** — Real-time layer (4a + 4b + 4c shipped)
- ✅ **Phase 5** — Policy ingestion + rule engine
  - ✅ 5a: Policies + chunks + rules schema
  - ✅ 5b: Rule expression evaluator + idempotent seed
  - ✅ 5c: Policy embedding pipeline + pgvector RAG search
- ✅ **Phase 6** — Alerts + 15-min restroom rule (complete)
- ✅ **Phase 7** — OpenAI Codex agent loop wrapping the tool surface
- ✅ **Phase 8** — Inter-agent boundary endpoints (complete)
- ✅ **Demo wire-up** — Periodic dispatcher loop tying `detect_overdue_passes` to `dispatch_alert`
- ✅ **Frontend integration** (3 steps; see "Frontend integration" below for the runbook)
  - ✅ Step 1: Top-level FastAPI app composing WS + agent boundary + browser REST + CORS (`32ca082`)
  - ✅ Step 2: Browser-facing REST router at `/api/*`, demo seed CLI, migration 0009 expanding hall pass destinations (`534ba4a`)
  - ✅ Step 3: Frontend wired to backend — `mockData.ts` deleted, pages call REST + subscribe over WebSocket (`e54a128`)
- ⏭ **Phase 9** — Audit log + observability hardening (post-hackathon)

## Frontend integration

Three commits stitch the React/Vite frontend in `frontend/` to the backend in this repo. With both running locally, clicking a student in the UI actually issues a hall pass on the backend, and overdue alerts land back in the UI live over WebSocket.

**Run both stacks locally:**

```bash
make db-up
.venv/bin/alembic upgrade head
.venv/bin/python -m hpao.cli.seed                       # demo school + classes + students (idempotent)
.venv/bin/uvicorn --factory hpao.app:app_factory --reload --port 8000

cd frontend && npm install && npm run dev               # http://localhost:3000
```

**What happens when you click through the UI:**

1. **ClassSelectPage** → `GET /api/sessions` returns today's class sessions for the demo school.
2. **RosterPage** → `GET /api/sessions/{id}/students` returns the roster + active passes, then opens a WebSocket to `class:<classId>` and `school:<schoolId>` so any subsequent server-side event triggers a refetch.
3. **DestinationPage** → no API call; just navigation state.
4. **PassActivePage** → `POST /api/hall-passes` issues the pass; teacher is inferred from the session's class.
5. **CheckedOutCard "Tap to Check-in"** → `POST /api/hall-passes/{id}/return`.

**Live overdue alert demo:** in a third terminal, `DISPATCHER_INTERVAL_SECONDS=5 python -m hpao.cli.dispatcher`. Issue a pass with `duration_minutes=1`; within 5 seconds the dispatcher flips it to `OVERDUE`, raises an alert, posts to parent-comms (if `PARENT_COMMS_URL` is set), and the WS event lands at the UI which refetches automatically.

**Deploying the frontend to Netlify:** the existing `netlify.toml` already builds from `frontend/`. Set `VITE_API_URL` and `VITE_WS_URL` in Netlify dashboard → Site settings → Environment, pointing at an ngrok / cloudflared tunnel of the local backend (HTTPS pages can't reach `ws://localhost`).

## Demo runbook (backend-only headline flow)

For demoing the 15-min restroom alert without the frontend in the loop:

1. `make db-up`
2. Set env: `DATABASE_URL=postgresql+asyncpg://hpao:hpao@localhost:5432/hpao`,
   `PARENT_COMMS_URL=https://your-teammate-agent.example`,
   `PARENT_COMMS_SECRET=<shared HMAC secret>`,
   `DISPATCHER_INTERVAL_SECONDS=5`
3. `.venv/bin/alembic upgrade head`
4. `python -m hpao.cli.dispatcher` — dispatcher loop in one terminal
5. In another terminal, issue a hall pass via the service (or hit `POST /api/hall-passes` from the UI / curl) with `duration_minutes=1`
6. Watch the dispatcher log — within `DISPATCHER_INTERVAL_SECONDS` the pass flips to `OVERDUE`, an alert is raised, and a signed POST hits parent-comms

Single iteration without the loop: `python -m hpao.cli.dispatcher --once`.

Without `PARENT_COMMS_URL` / `PARENT_COMMS_SECRET` set, the dispatcher still runs
`detect_overdue_passes` for state hygiene but skips outbound webhooks.

## All phases

| # | Phase | Status | Adds |
|---|---|---|---|
| 0 | TDD harness + bootstrap | ✅ done | pyproject, ruff/mypy, pre-commit gate, CI, docker-compose, CLAUDE.md |
| 1 | Domain models | ✅ done | Schools, Students, Users, Classes, Enrollments, Class Sessions |
| 2 | Attendance core | ✅ done | `attendance_records` + service for record/edit/list, source tracking, idempotency on (session, student) |
| 3 | Hall passes | ✅ done | `hall_passes` + check-out/in service, active-pass invariant, overdue detection |
| 4 | Real-time layer | ✅ done (other agent) | Postgres `LISTEN/NOTIFY` → WebSocket fan-out with `school:` / `class:` / `student:` channel scoping |
| 5 | Policy ingestion + rule engine | ✅ done (other agent) | `policies`, `policy_chunks` (pgvector), `policy_rules`, evaluator, embedding pipeline, RAG search |
| 6 | Alerts + threshold detection | ✅ done | `alerts`, raise/ack/resolve, partial unique on OPEN per (student, rule), 15-min restroom detect_overdue_passes wired |
| 7 | Agent layer | ✅ done | OpenAI Agents SDK loop + 8-tool surface (attendance, hallpass, alerts, policy, dispatch). CLI: `python -m hpao.cli.agent "..."` |
| 8 | Inter-agent boundary | ✅ done | REST endpoints + HMAC-signed outbound webhook to parent-comms agent |
| 9 | Audit + observability | ⏭ | `audit_log`, structured logging, LLM token budget + circuit breaker |

## Critical path for hackathon demo

Demo-minimum: **Phases 1–4 + 6 + 8**.

Flow that demo must show:
1. Teacher takes attendance → real-time event hits dashboard channel (Phases 1–2, 4)
2. Student checks out for restroom → pass starts ticking (Phase 3)
3. 15 minutes pass without check-in → alert raised (Phase 6)
4. Outbound webhook fires → teammate's parent-comms agent receives the intent (Phase 8)

Phase 5 (policy RAG) and Phase 7 (full agent loop) elevate it from demo to product. Skip if the clock runs out.

Phase 4 (real-time) is intentionally early — both rules engine and agent emit events through it, so getting the channel + WebSocket plumbing right pays compounding interest.

Phase 9 is post-hackathon unless judges care about audit trails.

## Ownership

This repo is shared with several agents working in parallel. Practical rules to keep merges painless:

- **Pull/fetch before every push.** Migrations are numbered, so two agents picking the same `0005_*` causes an alembic head split.
- **Stay in your lane.** Realtime owners don't touch service code; service authors don't reshape `src/hpao/realtime/`.
- **Frontend code lives under `frontend/`** and pulls types from `src/hpao/schemas/frontend.py`. The Pydantic schemas are the single source of truth for wire shapes — keep them in sync byte-for-byte with the TypeScript types in `frontend/src/api/types.ts`.

## Conventions (followed per phase)

- Red → green → refactor at the service-layer boundary.
- One migration per logical sub-phase. Migrations hand-written until the schema is large enough to justify autogen. **Wrap constraint names in `op.f(...)`** when dropping or recreating, so the naming convention isn't reapplied on top of an already-formatted name (see migration 0009 for the gotcha).
- Pre-commit gate runs unit tests on every commit. Pre-push runs full suite (integration auto-skips when Docker is off; CI always has Docker).
- Add factories for every new entity in `tests/factories.py`.
- Update `CLAUDE.md` if a contract changes.
- New tables get UUID PK, `created_at` / `updated_at` (TIMESTAMPTZ), and DB-level constraints (FK, UNIQUE, CHECK).
- Browser-facing JSON uses **camelCase**, internal Pydantic stays snake_case. Use `Field(serialization_alias=...)` / `validation_alias=...` to bridge — see `src/hpao/schemas/frontend.py`.
- Browser-facing endpoints don't sign HMAC; they go in `src/hpao/api/frontend.py`. Inter-agent endpoints sign HMAC; they go in `src/hpao/api/agent.py`. Don't mix.
- Tests for browser routes use **`httpx.AsyncClient` + `ASGITransport`** (not FastAPI `TestClient`) so the test, fixtures, and route handlers all share one event loop and one transactional session.

## Currently working on

Stack is functionally complete. Phase 9 (audit trail + observability hardening) is the only open item, and only matters if judges care about it — pre-hackathon cleanup if there's time, otherwise post-event.
