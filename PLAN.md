# HPAO Implementation Plan

Living doc. Update after each phase ships.

## Status

- ✅ **Phase 0** — TDD harness + bootstrap (pushed)
- ✅ **Phase 1** — Domain models (complete)
  - ✅ 1a: Persistence scaffolding (`d493122`)
  - ✅ 1b: Schools + Students (`110d7d0`)
  - ✅ 1c: Users + Classes + Enrollments + Class Sessions
- ✅ **Phase 2** — Attendance core (complete)
- 🔄 **Phase 3** — Hall passes (in progress)

## All phases

| # | Phase | Status | Adds |
|---|---|---|---|
| 0 | TDD harness + bootstrap | ✅ done | pyproject, ruff/mypy, pre-commit gate, CI, docker-compose, CLAUDE.md |
| 1 | Domain models | ✅ done | Schools, Students, Users, Classes, Enrollments, Class Sessions |
| 2 | Attendance core | 🔄 in progress | `attendance_records` + service for record/edit/list, source tracking, idempotency on (session, student) |
| 3 | Hall passes | 🔄 in progress | `hall_passes` + check-out/in service, active-pass invariant, overdue detection |
| 4 | Real-time layer | 🔵 owned by another agent | Postgres `LISTEN/NOTIFY` → WebSocket fan-out with `school:` / `class:` / `student:` channel scoping |
| 5 | Policy ingestion + rule engine | ⏭ | `policies`, `policy_chunks` (pgvector), `policy_rules`, evaluator, seed rules from TEC + PfISD |
| 6 | Alerts + threshold detection | ⏭ | `alerts`, triggers (write + overdue + nightly), 15-min restroom rule wired to on-duty admin |
| 7 | Agent layer | ⏭ | OpenAI Codex agent loop + tool surface (attendance, hallpass, rules, policy, alert, relay) |
| 8 | Inter-agent boundary | ⏭ | REST endpoints + HMAC-signed outbound webhook to parent-comms agent |
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

- **🔵 Phase 4 (real-time)** is being implemented by a separate coding agent in parallel. This repo is shared.
- The seam stays clean by design: Phases 2 / 3 / 6 just write to the DB; the Phase 4 layer reads those writes via `LISTEN/NOTIFY` triggers and fans them out. No code-level coupling between the agents.
- Pull/fetch before every push to integrate the other agent's work.
- Don't edit `src/hpao/realtime/`, NOTIFY trigger migrations, or WebSocket endpoints — those belong to the other agent.

## Conventions (followed per phase)

- Red → green → refactor at the service-layer boundary.
- One migration per logical sub-phase. Migrations hand-written until the schema is large enough to justify autogen.
- Pre-commit gate runs unit tests on every commit. Pre-push runs full suite (integration auto-skips when Docker is off; CI always has Docker).
- Add factories for every new entity in `tests/factories.py`.
- Update `CLAUDE.md` if a contract changes.
- New tables get UUID PK, `created_at` / `updated_at` (TIMESTAMPTZ), and DB-level constraints (FK, UNIQUE, CHECK).

## Currently working on

Phase 1 complete. Ready to start **Phase 2 — Attendance core** when given the go-ahead. Phase 2 plan: `attendance_records` table (one row per session × student, status enum, source enum, FK to class_sessions + students), service layer with idempotent record/edit, integration tests for the (session, student) UNIQUE invariant and source tracking.
