# Qualyx Development Guide

## 1. Purpose

This guide describes the local development workflow for Qualyx. Follow the instructions from the repository root unless a step explicitly specifies a component directory.

## 2. Prerequisites

Install:

- Git
- Python 3.12
- Node.js 22 with npm
- Docker Desktop and Docker Compose
- The Chromium dependencies required by Playwright

Check the installed versions:

```powershell
git --version
python --version
node --version
npm --version
docker --version
docker compose version
```

If the `python` command points to a different installation, use the Python 3.12 executable explicitly.

## 3. Repository Workflow

Use the `main` branch as the project's working branch under the current repository workflow.

Before starting a task:

```powershell
git status
git branch --show-current
```

Keep changes limited to the task being implemented. Review the diff before committing:

```powershell
git diff --check
git diff
git status
```

Do not commit secrets, local environment files, virtual environments, generated build output, or installed dependencies.

## 4. Database Setup

Start the local PostgreSQL service from the repository root:

```powershell
docker compose up -d
docker compose ps
```

Confirm the database is healthy before continuing.

Stop the service when it is no longer required:

```powershell
docker compose down
```

This command retains the named database volume. To preserve local data, do not remove the volume.

## 5. Backend Setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

If the virtual environment already exists, activate it instead of recreating it.

Create a local `.env` file from `.env.example` and set the required local values. Do not commit `.env`.

The documented local database URL is:

```text
postgresql+psycopg2://qualyx_user:qualyx_password@localhost:5432/qualyx
```

Use the credentials and port configured in the root `docker-compose.yml`. The example URL is for local development only; do not use these example credentials in production.

## 6. Database Migrations

Run these commands from the `backend` directory with the virtual environment activated:

```powershell
alembic upgrade head
alembic current
```

To inspect available migration history:

```powershell
alembic history
```

When making schema changes, create a new migration, review the generated operations, and test both migration application and application behavior. Do not edit an already-applied migration casually.

## 7. Backend Tests

From the `backend` directory:

```powershell
python -m pytest
```

Run tests after backend changes and investigate failures before committing.

## 8. Intelligence Tests

From the repository root, install the intelligence development dependencies:

```powershell
python -m pip install -r intelligence/requirements-dev.txt
```

Run the intelligence tests:

```powershell
python -m pytest intelligence/tests -v
```

Use an appropriate Python environment and install any additional runtime dependencies required by the implemented intelligence modules.

## 9. Execution Engine

From the repository root:

```powershell
cd execution-engine
npm ci
npx playwright install chromium
npm test
```

The engine's test suite may require browser dependencies and available local ports. If tests fail, inspect the error output rather than assuming the cause is the application code.

## 10. Recorder

From the repository root:

```powershell
cd recorder
npm ci
npm test
```

Run the tests after modifying recorder behavior or dependencies.

## 11. Dashboard

From the repository root:

```powershell
cd dashboard
npm ci
npm run build
```

Use any additional scripts defined in `dashboard/package.json` when needed.

## 12. Demo Application

From the repository root:

```powershell
cd demo-app
npm ci
npm run build
```

Check `demo-app/package.json` for the available development and test scripts.

## 13. Continuous Integration

The GitHub Actions workflow is configured to run the component-level checks for the backend, intelligence component, execution engine, recorder, dashboard, and demo app.

Before publishing a change:

1. Run the relevant local checks.
2. Review `git diff --check`.
3. Review the changed files.
4. Commit the focused change.
5. Push when ready to trigger GitHub Actions.
6. Inspect each CI job and resolve failures before treating the change as verified.

Local checks and CI checks should be reported separately.

## 14. Troubleshooting

### Database connection errors

- Confirm Docker is running.
- Check `docker compose ps`.
- Verify the configured database URL, port, username, and password.
- Confirm the database health check passes.
- Apply migrations before using database-backed workflows.

### Python dependency errors

- Activate the intended virtual environment.
- Check the Python version.
- Install both runtime and development requirements where appropriate.

### Node.js or Playwright errors

- Use the repository's expected Node.js version.
- Run `npm ci` in the relevant component directory.
- Install the browser dependencies required by Playwright.
- Read the full test output before changing code.

### Build or test failures

- Identify the failing component and exact command.
- Reproduce the failure locally where possible.
- Make the smallest relevant change.
- Rerun the failing check and then any related checks.

## 15. Development Standard

Document implemented behavior accurately. Keep setup instructions synchronized with actual scripts and configuration. A passing component test is not proof that the full platform is integrated, deployed, secure, or production-ready.
