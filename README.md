# Ava Attendance Officer

Ava Attendance Officer is a hackathon prototype for a high-school attendance workflow that connects classroom attendance, student hall-pass behavior, core policy logic, and guardian outreach into one loop.

The system has four equal parts:

```mermaid
flowchart LR
  Teacher["Teacher Dashboard"]
  HallPass["Hall Pass iPad"]
  Voice["Voice Agent"]

  subgraph Ava["Ava"]
    Data["Data"]
    Logic["Logic"]
    Policy["Policy"]
  end

  Teacher <--> Ava
  HallPass --> Ava
  Ava <--> Voice
```

- **Teacher Dashboard**: teachers view students, attendance history, and status, then record present, absent, excused, and unexcused outcomes.
- **Student Hall Pass App**: students start and return hall passes from an iPad-style web app, creating time-out-of-class events for Ava to analyze.
- **Ava Core Data, Logic, And Policy**: Ava ingests attendance and hall-pass events, keeps the canonical student timeline, evaluates trends and policy thresholds, and queues the next action.
- **Outbound Voice Agent**: Ava calls guardians in multiple languages, asks for context on absences or excessive hall-pass usage, and records confirmed explanations back to the datastore.

## Use Cases

### Teacher Records Attendance

```mermaid
flowchart LR
  A["View Dashboard"] --> B["Update Status"]
  B --> C["Dashboard updates with resolved, pending, or needs-call state"]
```

### Student Uses Hall Pass

```mermaid
flowchart LR
  A["Start Hall Pass"] --> B["Return Hall Pass"] --> C["Ava Saves"]
  C --> D["Ava saves hall-pass reason, duration, and student timeline"]
```

### Ava Evaluates Risk And Policy

```mermaid
flowchart LR
  A["Ingest"] --> B["Analyze"] --> C["Queue Action"]
  C --> D["Ava maintains data, logic, policy, and work queues"]
```

### Voice Agent Calls Guardian

```mermaid
flowchart LR
  A["Load Students"] --> B["Call Guardian"] --> C["Record Conversation"]
  C --> D["Ava records transcript, excuse, language, and follow-up status"]
```


## Prerequisites

Pinned versions live in `pyproject.toml` (`requires-python = ">=3.12"`), `.python-version`, `.tool-versions`, `frontend/package.json` (`engines`), and `outbound-voice-agent/package.json` (`engines`). The full matrix:

| Tool | Required version | Why | Quick install |
|---|---|---|---|
| **Python** | 3.12 or newer (3.13 also tested) | Backend runtime + alembic + pytest | macOS: `brew install python@3.12` · Linux: `apt install python3.12 python3.12-venv` · Windows: [python.org installer](https://www.python.org/downloads/) · pyenv: `pyenv install 3.12 && pyenv local 3.12` (reads `.python-version`) · asdf: `asdf install` (reads `.tool-versions`) |
| **pip** | 24+ | Resolves `pyproject.toml` extras | Bundled with Python; `python3 -m pip install --upgrade pip` |
| **Node.js** | 20.x or newer | Frontend (Vite) + Outbound Voice Agent | macOS: `brew install node@20` · nvm: `nvm install 20 && nvm use 20` · asdf: `asdf install` |
| **npm** | 10+ | Bundled with Node 20+ | (comes with Node) |
| **Docker Desktop** / Docker Engine | 20.10+ with Compose v2 | Local Postgres 16 + pgvector via `docker-compose.yml` | macOS / Windows: [Docker Desktop](https://www.docker.com/products/docker-desktop/) · Linux: `apt install docker.io docker-compose-plugin` |
| **PostgreSQL** | 16 + pgvector extension | Database. Pulled automatically as the `pgvector/pgvector:pg16` image — no host install needed when you use Docker | (handled by `docker compose up db`) |
| **OpenAI API key** | — | Phase 5c policy embeddings + Phase 7 agent + Outbound Voice Agent. Tests stub it out. | Generate at [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **git** | 2.30+ | Standard | Comes with Xcode CLI / `apt install git` / Git for Windows |

`make`, `curl`, and a POSIX shell (the `quickstart.sh` script targets Bash 4+ / Zsh) round out the system tooling. Everything else is Python-managed inside `.venv/` or Node-managed inside `frontend/node_modules/` and `outbound-voice-agent/node_modules/` — no global installs needed.

> If you're using **pyenv**, `.python-version` will trigger an auto-install on first `cd`. If you're using **asdf**, `.tool-versions` covers both Python and Node — run `asdf install` once at the repo root.

### Verifying your environment

```bash
python3 --version    # should print Python 3.12.x or 3.13.x
node --version       # should print v20.x or higher
npm --version        # should print 10.x or higher
docker --version     # any 20.10+ release
docker compose version
```

If any of those fail, fix that tool before running `quickstart.sh`. The script does an explicit Python ≥ 3.12 preflight and exits with a clear message if the wrong version is found; other tools surface their failures further along, so it's worth running these five commands first.

### Recommended: auto-activate the venv with `direnv`

`quickstart.sh` and `make install` create a `.venv/` at the repo root. To make `python`, `pytest`, `alembic`, etc. resolve to the venv automatically whenever you `cd` into the repo (no `source .venv/bin/activate` ritual, no `.venv/bin/` prefixing):

```bash
brew install direnv                                # or: apt install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc      # or .bashrc
cd hallPassAttendanceOfficer
direnv allow .                                     # one-time, accepts the checked-in .envrc
```

The `.envrc` we ship is a single conditional `source .venv/bin/activate`, so it's a no-op until `quickstart.sh` creates the venv, then it activates on the next prompt. Optional but strongly recommended.

## Quick Start

Create the demo environment file and add your OpenAI API key:

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY.
```

Then run the root quickstart script:

```bash
chmod +x quickstart.sh
./quickstart.sh
```

The script installs the backend/core Python package, starts local Postgres when Docker is available, runs alembic migrations, seeds a demo school + classes + students, brings up the Ava backend (FastAPI) on `:8000`, installs the Teacher Dashboard / Hall Pass iPad frontend, installs the Outbound Voice Agent, starts both local web servers wired against the backend (`VITE_API_URL=http://localhost:8000`), and opens:

- Teacher Dashboard: `http://localhost:3100/`
- Hall Pass iPad:    `http://localhost:3000/` (same app — pick a class, then a student)
- Swagger API Docs: `http://localhost:8000/docs`
- Outbound Voice Agent: `http://localhost:5178`

## Demo Flow

1. Run `./quickstart.sh`.
2. Use the Teacher Dashboard tab to view classes and roster status.
3. Use the Hall Pass iPad tab to select a student and hall-pass destination.
   1. Click login button
   2. Select a student
   3. Select reason for hall pass to initiate the hall pass
4. Use the Outbound Voice Agent tab to click `Start Call`.
   1. Allow microphone access, then click `Enable Mic` when ready to answer as the guardian.
   2. Ava starts with a bilingual guardian identity check.
   3. The guardian can answer in English or Spanish. Short replies are handled with explicit rules: `yes` selects English, `si` or `sí` selects Spanish, and ambiguous `no` falls back to the datastore guardian language.
   4. Ava asks for the reason, summarizes it, asks for confirmation, and saves the outcome.
   5. The transcript pane shows the spoken Ava and guardian turns.

Sample `.env`:

```bash
OPENAI_API_KEY=sk-your-api-key
DATABASE_URL=postgresql+asyncpg://hpao:hpao@localhost:5432/hpao
PORT=5178
FRONTEND_PORT=3000
SAFETY_IDENTIFIER=outbound-voice-agent-local
```

## Tech Stack

- **Outbound Voice Agent**: Node.js 20+ ESM HTTP server using built-in `node:http`, browser WebRTC audio, plain HTML/CSS/JavaScript, OpenAI Realtime API with `gpt-realtime-2`, `gpt-4o-transcribe`, semantic VAD turn detection, and Realtime function calling.
- **Voice Demo Datastore**: CSV fixtures and outputs under `outbound-voice-agent/data`, with local endpoints for case loading, transcript logging, and confirmed excuse recording.
- **Teacher Dashboard / Hall Pass iPad**: React 18, TypeScript, Vite 5, React Router, Tailwind CSS, and lucide-react. The frontend calls the Ava backend over `/api/*` for class lists, rosters, and hall-pass state, and subscribes to `/v1/realtime` over WebSocket for live updates.
- **Ava Core Backend**: Python 3.12 package with FastAPI, Pydantic v2, Pydantic Settings, SQLAlchemy 2 async, asyncpg, Alembic migrations, PostgreSQL 16, and pgvector.
- **Policy And Logic Layer**: Python services for attendance, hall passes, alerts, policy rules, policy ingestion/search, and realtime event publishing.
- **Local Infrastructure**: Docker Compose starts `pgvector/pgvector:pg16`; `quickstart.sh` prepares the Python venv, installs Node apps, starts demo servers, and opens the three local demo URLs.
- **Quality Tooling**: pytest, pytest-asyncio, pytest-cov, testcontainers, factory-boy, freezegun, hypothesis, ruff, mypy, pre-commit hooks, and GitHub Actions CI for Python lint/typecheck/unit/integration tests.

## How It Works

### Teacher Dashboard

The Teacher Dashboard is part of the React/Vite frontend in `frontend/`. It uses React Router to move from login to class selection to a roster view. The dashboard reads class sessions and rosters from the Ava backend (`GET /api/sessions`, `GET /api/sessions/{id}/students`) and opens a WebSocket against `/v1/realtime` so newly issued or returned passes refetch live without a manual reload. Teachers can view the current class, see in-class and checked-out counts, tap student roster entries, and move into the hall-pass flow.

Demo URL: `http://localhost:3000/classes`

### Hall Pass iPad App

The Hall Pass iPad app is the same frontend app, shown at a student-facing route. A student is selected from the roster, chooses a destination, and sees an active pass screen. Issuing the pass calls `POST /api/hall-passes` against the Ava backend; checking back in calls `POST /api/hall-passes/{id}/return`. The class session's WebSocket subscription means a pass issued from one device shows up on every other dashboard pointed at the same class within milliseconds.

Demo URL: open the Teacher Dashboard at `http://localhost:3000/classes`, pick a class, then tap a student.

### Core Data, Logic, And Policy

The core backend lives under `src/hpao/`. It defines the durable domain model for schools, students, users, classes, class sessions, attendance records, hall passes, policies, and alerts. SQLAlchemy models and Alembic migrations target PostgreSQL with pgvector. Service modules implement attendance recording, hall-pass issue/return behavior, alert detection, and policy/rule evaluation. The realtime package publishes and serves event streams for dashboard-style consumers.

During the hackathon demo, the frontend drives the backend directly: every class lookup, roster fetch, and hall-pass action is a real database write through the FastAPI `/api/*` surface. The outbound voice agent still runs against its own CSV fixtures rather than the shared backend — joining those two stores is a post-hackathon item.

### Outbound Voice Agent

The outbound voice agent lives in `outbound-voice-agent/`. Its local Node server keeps the OpenAI API key server-side, serves the browser UI, loads synthetic student/policy context from CSV, creates OpenAI Realtime WebRTC sessions, and records demo outputs back to CSV.

The browser captures microphone audio through WebRTC and sends it to the OpenAI Realtime session created by the local server. The server builds the Realtime session config in `outbound-voice-agent/src/session-config.mjs`, including:

- `model: "gpt-realtime-2"`
- `audio.input.turn_detection.type: "semantic_vad"`
- `audio.input.turn_detection.create_response: true`
- `audio.input.turn_detection.interrupt_response: false`
- `audio.input.transcription.model: "gpt-4o-transcribe"`
- `tools[0].name: "submit_attendance_excuse"`

The browser sends a scenario-specific opening instruction for the combined attendance and hall-pass call. When the guardian confirms a reason, the model calls `submit_attendance_excuse`; the browser posts that tool call to `/attendance-excuse`, writes a mocked row to CSV, and sends the tool result back into the Realtime session.

Outbound voice demo endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /case` | Load the current synthetic student case |
| `POST /session` | Exchange browser SDP for an OpenAI Realtime WebRTC answer |
| `POST /conversation-log` | Append transcript rows to the demo datastore |
| `POST /attendance-excuse` | Append confirmed guardian explanation to the demo datastore |
