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
