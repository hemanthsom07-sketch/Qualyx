"""
Qualyx Backend — FastAPI application entrypoint.

Scope for this milestone (per Task 3):
- App startup
- Health check
- Project create/retrieve

Deliberately NOT included yet (per contract restrictions in Task 3):
- RecordedJourney, TestDefinition, ExecutionRequest, ExecutionResult,
  FailureDiagnosis, HealingProposal endpoints
- Any Playwright execution wiring
- Any diagnosis/healing logic

Those will be added in later milestones once the relevant shared
contracts/schemas are materialized in /shared.
"""

from fastapi import FastAPI

from app.api.routes import health, projects
from app.config import settings
from app.database import init_db

app = FastAPI(title="Qualyx Backend", version="0.1.0")

app.include_router(health.router)
app.include_router(projects.router)


@app.on_event("startup")
def on_startup() -> None:
    if settings.db_auto_create:
        # Local-dev convenience only — see database.init_db() docstring.
        init_db()
