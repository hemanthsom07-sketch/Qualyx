"""
Qualyx Backend — FastAPI application entrypoint.

Scope as of Task 6:
- App startup
- Health check
- Project create/retrieve (Task 3)
- TestDefinition create/retrieve/list, scoped under a Project (Task 4,
  backend-internal representation — not the frozen cross-module
  TestDefinition contract; see app/models/test_definition.py docstring)
- TestDefinition execution via the Execution Engine subprocess boundary
  (Task 6 — see app/services/execution_client.py). No browser automation
  happens in Python; this only invokes and reports the engine's result.

Deliberately NOT included yet:
- RecordedJourney, ExecutionRequest (as a stored/queued entity),
  FailureDiagnosis, HealingProposal cross-module contract endpoints
- Any diagnosis/healing/classification logic (Claude 3's domain)

Those will be added in later milestones once the relevant shared
contracts/schemas are materialized in /shared.
"""

from fastapi import FastAPI

from app.api.routes import health, projects, test_definitions
from app.config import settings
from app.database import init_db

app = FastAPI(title="Qualyx Backend", version="0.1.0")

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(test_definitions.router)


@app.on_event("startup")
def on_startup() -> None:
    if settings.db_auto_create:
        # Local-dev convenience only — see database.init_db() docstring.
        init_db()
