# Qualyx Backend (Claude 2 — Milestone 1)

Minimal FastAPI + PostgreSQL + SQLAlchemy foundation.

Scope of this milestone: app startup, health check, and Project
create/retrieve. No cross-module contracts (RecordedJourney,
TestDefinition, ExecutionRequest, ExecutionResult, FailureDiagnosis,
HealingProposal) are implemented yet.

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
