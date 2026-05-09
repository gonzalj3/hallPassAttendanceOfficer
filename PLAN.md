# HPAO Implementation Plan

Living doc. Update after each phase ships.

## Status

- ✅ **Phase 0** — TDD harness + bootstrap (pushed)
- 🔄 **Phase 1** — Domain models (in progress)
  - ✅ 1a: Persistence scaffolding (`d493122`)
  - ✅ 1b: Schools + Students (`110d7d0`)
  - ⏭ 1c: Users + Classes + Enrollments + Class Sessions

## All phases

| # | Phase | Status | Adds |
|---|---|---|---|
| 0 | TDD harness + bootstrap | ✅ done | pyproject, ruff/mypy, pre-commit gate, CI, docker-compose, CLAUDE.md |
| 1 | Domain models | 🔄 partial | Schools+Students done; Users, Classes, Enrollments, Class Sessions remaining |
| 2 | Attendance core | ⏭ | `attendance_records` + service for record/edit/list, source tracking, idempotency on (session, student) |
| 3 | Hall passes | ⏭ | `hall_passes` + check-out/in service, active-pass invariant, overdue detection |
| 4 | Real-time layer | ⏭ | Postgres `LISTEN/NOTIFY` → WebSocket fan-out with `school:` / `class:` / `student:` channel scoping |
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

## Conventions (followed per phase)

- Red → green → refactor at the service-layer boundary.
- One migration per logical sub-phase. Migrations hand-written until the schema is large enough to justify autogen.
- Pre-commit gate runs unit tests on every commit. Pre-push runs full suite (integration auto-skips when Docker is off; CI always has Docker).
- Add factories for every new entity in `tests/factories.py`.
- Update `CLAUDE.md` if a contract changes.
- New tables get UUID PK, `created_at` / `updated_at` (TIMESTAMPTZ), and DB-level constraints (FK, UNIQUE, CHECK).

## Currently working on

**Phase 1c** — Users (TEACHER/ADMIN/COUNSELOR/NURSE), Classes, ClassEnrollments (M2M with UNIQUE per class+student), ClassSessions (UNIQUE per class+date). One migration (`0002`), one commit.
