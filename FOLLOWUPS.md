# Follow-ups

Loose ends from the MVP cutover (Phases A–I, merged to `main` on 2026-06-06).
Nothing here blocks shipping new features. Pick items off this list when a
related area is open in front of you anyway.

## Security

### Rotate the leaked OpenAI API key
- **What:** the key starting `sk-svcacct-3xtFBpTfG...` and project ID
  `proj_c6eMBzHZ13vhG9UFn0wPDTof` landed in the agent transcript on 2026-06-06
  when an `.env` file was inspected during deployment. Even though Monitor
  Lizzie no longer calls OpenAI, the key is still live on the account.
- **How:** https://platform.openai.com/api-keys → trash icon → confirm.
- **Priority:** do it now.

### Audit log read paths (pilot-only)
- Today only hall-pass mutations and admin deletes write `audit_log` rows.
  For a real Texas pilot under FERPA §99.32, every read of student PII has
  to be logged too. The schema (`actor_role`, `action`, `target_type`,
  `target_id`, `context`) already supports this — turn it on by adding
  `await write_audit(...)` calls in `src/lizzie/api/frontend.py` at every
  read endpoint when a real pilot is on the horizon.

## Deployment / infra

### Railway URL still says `hpao-backend-production`
- **What:** the service was renamed to `monitor-lizzie-backend` in the
  dashboard, but the auto-generated `*.up.railway.app` URL is pinned at
  creation time and didn't update. So the public URL is still
  `https://hpao-backend-production.up.railway.app`.
- **Cost of leaving it:** purely cosmetic. Two callers reference it:
  `frontend/netlify.toml` and `frontend-dashboard/netlify.toml`.
- **How to fix if it ever matters:** mint a new generated domain via the
  Railway GraphQL `serviceDomainCreate` mutation (or in the dashboard:
  Service → Settings → Networking → Generate Domain), then update both
  `netlify.toml` files' redirect targets and redeploy.

### Stale Railway service config overrides
- The hackathon-era `hpao-backend` service had three GraphQL-stored
  overrides that ignored `railway.json` and crashed every deploy:
  - `startCommand: "sh -c 'uvicorn --factory hpao.app:app_factory ...'"`
  - `railwayConfigFile: ".railway.disabled.json"`
  - `builder: RAILPACK`
- They're cleared now. If you ever recreate a Railway service from scratch
  and see deploys mysteriously failing, check the same three fields via:
  ```graphql
  query {
    service(id: "<service-id>") {
      serviceInstances { edges { node {
        startCommand railwayConfigFile builder dockerfilePath
      } } }
    }
  }
  ```
  Clear with `serviceInstanceUpdate(input: { startCommand: "",
  railwayConfigFile: "railway.json" })`.

### Old `railway` Postgres database is gone
- Dropped on 2026-06-06. The hackathon-era schema (attendance_records,
  policies, agent_messages) is no longer recoverable. The two `legacy/*`
  git branches still have the code, but the production data is gone.

## Frontend

### Dashboard `AlertsPage` voice-call column
- `frontend-dashboard/src/pages/AdminDashboard.tsx` still has a "Voice
  Calls" column in the AlertsPage component that receives `voiceCalls=[]`
  and renders an empty state. The `VoiceCallsCard` on the overview page
  was deleted in Phase H, but the AlertsPage column wasn't — it's ~150
  lines of dead UI rendering nothing. Surgical cleanup any time someone
  is opening that file for something else.

### `ws://` fallback in dev for non-HTTPS pages
- `realtime.ts` derives `wss://` when `window.location.protocol === 'https:'`
  and `ws://` otherwise. Localhost dev is fine (no TLS). If anyone ever
  hosts the static site over plain HTTP somewhere, the WS will attempt
  `ws://` — and the Netlify proxy expects HTTPS. Document or harden when
  it actually comes up.

## Backend / tests

### Migration 0009 has a module-level `op.f()` call
- `alembic/versions/0009_expand_hall_pass_destinations.py` line 24 calls
  `op.f("ck_hall_passes_destination_valid")` at module load time. This
  works during `alembic upgrade head` (the `op` proxy is bound by then)
  but breaks `alembic history` and any offline tooling that parses the
  whole chain. Pre-existing from the hackathon; low-priority. Fix by
  moving the constant into `upgrade()` / `downgrade()`.

### Pre-commit runs the full integration suite on push
- `.pre-commit-config.yaml` runs unit on commit and full suite (including
  testcontainers + Docker) on push. Currently ~8s. Will get slower as the
  test suite grows; consider gating integration tests behind a flag, or
  moving them to CI-only once the project gets a real CI pipeline.

### No CI pipeline yet
- Pre-commit hooks are the only quality gate. GitHub Actions, Railway
  branch previews, or any other CI is unconfigured. Fine for solo demo
  work; add CI before inviting collaborators.

## Documentation

### CLAUDE.md and README assume local-dev defaults that may drift
- Both docs name port 8000 for the backend, port 3000 for the teacher
  iPad, port 3100 for the dashboard, `5433` for Postgres (under the
  override file). If anyone changes those locally, the docs lie. Cheap
  to fix when noticed; not worth a pass on its own.
