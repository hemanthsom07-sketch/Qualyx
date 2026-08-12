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
- Ingesting Claude 3's Intelligence execution payload directly
  ({"journeyId", "steps": [...]}) into a TestDefinition, via
  POST /projects/{project_id}/tests/from-execution-payload — see
  app/schemas/test_definition.py's ExecutionPayloadCreate docstring.
- Ingesting raw Recorder events directly (Day 1), via
  POST /projects/{project_id}/recordings — see
  app/api/routes/recordings.py. Events are run through Intelligence's
  existing generate_execution_payload_from_real_recorder_events()
  pipeline (app/services/intelligence_client.py) and stored the same
  way as the execution-payload endpoint above.
- CORS: an explicit local-dev origin allow-list (see app/config.py's
  cors_allowed_origins), not a wildcard.

Deliberately NOT included yet:
- RecordedJourney, ExecutionRequest (as a stored/queued entity),
  FailureDiagnosis, HealingProposal cross-module contract endpoints
- Any diagnosis/healing/classification logic (Claude 3's domain)

Those will be added in later milestones once the relevant shared
contracts/schemas are materialized in /shared.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, projects, recordings, test_definitions
from app.config import settings
from app.database import init_db

app = FastAPI(title="Qualyx Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(test_definitions.router)
app.include_router(recordings.router)


@app.on_event("startup")
def on_startup() -> None:
    if settings.db_auto_create:
        # Local-dev convenience only — see database.init_db() docstring.
        init_db()
