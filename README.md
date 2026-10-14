# Qualyx

**AI-Powered Intelligent QA and Self-Healing Testing Platform**

Qualyx is a software quality engineering project designed to make end-to-end testing more intelligent, explainable, and maintainable. Its intended workflow combines user-journey recording, automated test execution, failure analysis, and assisted test repair.

> **Project status:** Qualyx is under active development. Individual components have different levels of implementation and verification. The complete end-to-end workflow should not be considered production-ready until integration and deployment tests confirm it.

## Objectives

- Capture and represent user journeys as repeatable test scenarios.
- Generate and execute browser-based end-to-end tests.
- Collect execution results and diagnostic evidence.
- Help distinguish application failures from test instability.
- Investigate failed tests and identify likely causes.
- Support safer, evidence-based test maintenance and repair.

These are project objectives; availability depends on the implementation status of each component.

## Architecture

Qualyx is organized into the following components:

| Component | Responsibility |
|---|---|
| Dashboard | Web interface for interacting with the platform |
| Backend | API, application logic, and persistence |
| Execution engine | Browser-based test execution using Playwright |
| Recorder | Captures browser interactions for test creation |
| Intelligence | Analysis and diagnosis capabilities |
| Demo app | Application used for development and testing |

See [`docs/architecture.md`](docs/architecture.md) for the component relationships and design details.

## Technology Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **Browser automation:** Playwright
- **JavaScript/TypeScript tooling:** Node.js and npm
- **Testing:** pytest and component-specific test suites

Refer to each component's package or requirements files for its exact dependencies.

## Repository Structure

```text
Qualyx/
Γö£ΓöÇΓöÇ backend/
Γö£ΓöÇΓöÇ dashboard/
Γö£ΓöÇΓöÇ demo-app/
Γö£ΓöÇΓöÇ execution-engine/
Γö£ΓöÇΓöÇ intelligence/
Γö£ΓöÇΓöÇ recorder/
Γö£ΓöÇΓöÇ docs/
Γö£ΓöÇΓöÇ docker-compose.yml
ΓööΓöÇΓöÇ README.md
```

The structure above summarizes the main project components. Additional configuration and test files may exist within each directory.

## Prerequisites

Install the following tools before setting up the project:

- Git
- Python 3.12
- Node.js 22 and npm
- Docker Desktop with Docker Compose
- A supported Chromium installation through Playwright

Use the version and setup instructions required by the relevant component if they differ from these project defaults.

## Local Development

### 1. Clone or open the repository

If you have already downloaded the repository, open its root directory in VS Code.

### 2. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d
docker compose ps
```

Confirm that the database container is healthy before running database migrations.

### 3. Configure the backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

Create a local `.env` file based on `backend/.env.example` and configure the database connection for your local environment.

### 4. Apply database migrations

From the `backend` directory, with the virtual environment activated:

```powershell
alembic upgrade head
```

Do not use automatic table creation as a substitute for the migration workflow.

### 5. Run backend tests

From the `backend` directory:

```powershell
python -m pytest
```

### 6. Install frontend or Node.js component dependencies

For a Node.js component, open a terminal in its directory and run:

```powershell
npm ci
```

Run the scripts defined in that component's `package.json`. For example, use `npm run build` where a build script exists and `npm test` where a test script exists.

Consult [`docs/development.md`](docs/development.md) for the component-specific workflow.

## Continuous Integration

The GitHub Actions workflow in `.github/workflows/ci.yml` is intended to validate:

- Backend tests
- Intelligence tests
- Execution-engine tests
- Recorder tests
- Dashboard build
- Demo-app build

A successful local test does not prove that the complete workflow passes in GitHub Actions. Check the workflow results after pushing the relevant commits.

## Development Principles

- Keep changes focused and reviewable.
- Use database migrations for schema changes.
- Keep generated files, dependencies, secrets, and local environments out of version control.
- Verify commands and tests rather than assuming they succeeded.
- Separate test-selector repair from application-source-code repair.
- Preserve evidence and explain the reasoning behind automated diagnoses.
- Do not describe planned capabilities as implemented until verified.

## Documentation

- [Architecture](docs/architecture.md)
- [Development Guide](docs/development.md)

## Project Status

Qualyx is being developed incrementally. Architecture, setup instructions, test coverage, and integration status should be updated as implementation changes. Production readiness requires additional security, reliability, integration, and deployment validation.
