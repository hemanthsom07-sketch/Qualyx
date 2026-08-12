# Qualyx Backend (Claude 2 — Task 3 + Task 4 + Task 6)

Minimal FastAPI + PostgreSQL + SQLAlchemy foundation.

Scope as of Task 6: app startup, health check, Project create/retrieve
(Task 3), TestDefinition create/retrieve/list scoped to a Project
(Task 4), and executing a TestDefinition via the Execution Engine
(Task 6). TestDefinition remains a backend-internal representation for
this milestone, not the frozen cross-module TestDefinition contract (see
`app/models/test_definition.py`). No other cross-module contracts
(RecordedJourney, FailureDiagnosis, HealingProposal) are implemented yet.

The backend never implements browser automation itself — executing a
test invokes the existing Node/TypeScript Execution Engine as a
subprocess over a small JSON stdin/stdout protocol (see
`app/services/execution_client.py`).

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in real local values:

   ```bash
   cp .env.example .env
   ```

3. Ensure a local PostgreSQL instance is running and reachable at the
   `DATABASE_URL` you configured (see "PostgreSQL setup" below).

## Run

```bash
uvicorn app.main:app --reload
```

- Health check: `GET http://localhost:8000/health`
- Create project: `POST http://localhost:8000/projects`
- Get project: `GET http://localhost:8000/projects/{project_id}`
- List projects: `GET http://localhost:8000/projects`
- Create test definition: `POST http://localhost:8000/projects/{project_id}/tests`
- Get test definition: `GET http://localhost:8000/tests/{test_id}`
- List test definitions for a project: `GET http://localhost:8000/projects/{project_id}/tests`
- Execute a test definition: `POST http://localhost:8000/tests/{test_id}/execute`
- Ingest raw Recorder events: `POST http://localhost:8000/projects/{project_id}/recordings`

### Ingesting raw Recorder events

`POST /projects/{project_id}/recordings` accepts Recorder's actual
`RecordedEvent` contract verbatim:

```json
{
  "journeyId": "string",
  "events": [
    {
      "id": "string",
      "type": "page_load | click | input_change",
      "timestamp": 0,
      "pageUrl": "string",
      "targetTag": "optional string",
      "elementId": "optional string",
      "elementText": "optional string",
      "value": "optional string",
      "redacted": "optional boolean"
    }
  ]
}
```

It runs these events through Intelligence's existing
`generate_execution_payload_from_real_recorder_events()` pipeline (see
`app/services/intelligence_client.py`) and stores the result as a
TestDefinition — `journeyId` becomes the name, generated steps become
`content` — reusing the exact same validation/storage path as
`POST /projects/{project_id}/tests/from-execution-payload`.

Backend and Intelligence are both plain Python but live as sibling
packages with no installable packaging connecting them. This endpoint
requires the `intelligence/` package to be a sibling directory of
`backend/` (default) or reachable via `INTELLIGENCE_DIR` — see
`app/services/intelligence_client.py` for exactly how that's resolved.

Responses:
- `201` — recording ingested, TestDefinition created
- `404` — no such project
- `422` — malformed event data, empty events list, or Intelligence
  genuinely produced zero usable steps from the given events
- `502` — Intelligence's pipeline itself failed while processing

### Executing a test definition

`POST /tests/{test_id}/execute` re-validates the stored steps and runs
them via the Execution Engine subprocess. It requires Node.js and the
execution engine's dependencies to be set up (see
`../execution-engine/README.md`) and reachable at the path configured by
`EXECUTION_ENGINE_DIR` (defaults to a sibling `../execution-engine`
directory next to `backend/`).

Responses:
- `200` — execution ran (body's `status` is `"passed"` or `"failed"`;
  a failed *test* is still a successful API call)
- `404` — no such test definition
- `422` — the stored steps failed the engine's own validation
- `502` — the execution engine subprocess itself failed/timed out

## Tests

```bash
pytest
```

Tests use an in-memory SQLite database for isolation and do not require
a running PostgreSQL instance. This is a test-fixture choice, not an
architecture change — the application itself still targets PostgreSQL
by default (see `app/database.py`, `app/config.py`).

## PostgreSQL setup

The app expects a reachable PostgreSQL database matching `DATABASE_URL`.
Example local setup:

```bash
# Using Docker (optional, not committed as part of this milestone):
docker run --name qualyx-postgres \
  -e POSTGRES_USER=qualyx_user \
  -e POSTGRES_PASSWORD=qualyx_password \
  -e POSTGRES_DB=qualyx \
  -p 5432:5432 -d postgres:16

# Or install PostgreSQL locally and create a matching user/database.
```

On startup, if `DB_AUTO_CREATE=true`, the app will create tables
directly from the ORM models (convenience only — not a substitute for
real migrations, which should be introduced via Alembic in a later
milestone).

## CORS

The app allows an explicit list of local development origins (see
`app/config.py`'s `cors_allowed_origins`, default: Vite's dev server on
`5173` and a common alternate `3000`, on both `localhost` and
`127.0.0.1`) rather than a wildcard `allow_origins=["*"]`, since this API
has no authentication yet. Override via `CORS_ALLOWED_ORIGINS` if your
Dashboard runs on a different local port.

This does not necessarily cover the Recorder (a Chrome extension) —
extension-originated requests may or may not be subject to CORS at all,
depending on the extension's manifest permissions, which this repo's
Backend has no visibility into. If Recorder requests are blocked in
practice, its specific `chrome-extension://<id>` origin would need to
be added explicitly.
