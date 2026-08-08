"""
Tests for POST /projects/{project_id}/tests/from-execution-payload.

This endpoint ingests Claude 3's Intelligence execution payload
({"journeyId": ..., "steps": [...]}, as produced by
test_generation/execution_payload.py's to_execution_test_payload())
directly into a TestDefinition, reusing the existing storage/execution
machinery. See app/schemas/test_definition.py's ExecutionPayloadCreate
docstring for the exact contract this mirrors.

Like tests/test_execution.py, execute_steps() is mocked here rather than
spawning the real Node execution engine, so this suite stays
independently runnable.
"""

from unittest.mock import patch

from app.schemas.execution import ExecutionResultOut

# Representative payload shaped exactly like
# test_generation.execution_payload.to_execution_test_payload()'s output
# for a LocalGeneratedTest with one navigate step and one click step
# that has a selector_kind.
INTELLIGENCE_EXECUTION_PAYLOAD = {
    "journeyId": "journey-abc-123",
    "steps": [
        {"id": "gen-step-nav-1", "type": "navigate", "url": "https://example.com"},
        {
            "id": "gen-step-click-2",
            "type": "click",
            "selector": "#submit",
            "selectorKind": "data-testid",
        },
    ],
}


def _create_project(client, name="Intelligence Ingestion Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _passing_result() -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "passed",
            "steps": [
                {"stepIndex": 0, "id": "gen-step-nav-1", "type": "navigate", "status": "passed", "durationMs": 50},
                {"stepIndex": 1, "id": "gen-step-click-2", "type": "click", "status": "passed", "durationMs": 30},
            ],
            "failedStepIndex": None,
            "failedStepId": None,
            "error": None,
            "executedStepCount": 2,
            "startedAt": "2026-01-01T00:00:00.000Z",
            "finishedAt": "2026-01-01T00:00:00.100Z",
            "durationMs": 100,
            "evidence": None,
        }
    )


# --- 1. Intelligence-shaped payload is accepted ---

def test_execution_payload_is_accepted(client):
    project_id = _create_project(client)

    response = client.post(
        f"/projects/{project_id}/tests/from-execution-payload",
        json=INTELLIGENCE_EXECUTION_PAYLOAD,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert len(body["content"]) == 2


def test_execution_payload_requires_existing_project(client):
    response = client.post(
        "/projects/does-not-exist/tests/from-execution-payload",
        json=INTELLIGENCE_EXECUTION_PAYLOAD,
    )
    assert response.status_code == 404


# --- 2. journeyId becomes the TestDefinition name ---

def test_journey_id_becomes_test_definition_name(client):
    project_id = _create_project(client)

    response = client.post(
        f"/projects/{project_id}/tests/from-execution-payload",
        json=INTELLIGENCE_EXECUTION_PAYLOAD,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "journey-abc-123"


# --- 3. step IDs survive ingestion ---

def test_step_ids_survive_ingestion(client):
    project_id = _create_project(client)

    response = client.post(
        f"/projects/{project_id}/tests/from-execution-payload",
        json=INTELLIGENCE_EXECUTION_PAYLOAD,
    )

    content = response.json()["content"]
    assert content[0]["id"] == "gen-step-nav-1"
    assert content[1]["id"] == "gen-step-click-2"


# --- 4. selectorKind survives ingestion ---

def test_selector_kind_survives_ingestion(client):
    project_id = _create_project(client)

    response = client.post(
        f"/projects/{project_id}/tests/from-execution-payload",
        json=INTELLIGENCE_EXECUTION_PAYLOAD,
    )

    content = response.json()["content"]
    # stored under the same "selectorKind" key it arrived with, not the
    # Python-side "selector_kind" attribute name
    assert content[1]["selectorKind"] == "data-testid"
    assert "selector_kind" not in content[1]
    # the navigate step never had a selectorKind, and none should be
    # fabricated for it
    assert "selectorKind" not in content[0]


def test_source_step_id_and_source_event_id_are_not_accepted(client):
    """
    source_step_id/source_event_id are not part of Intelligence's
    execution payload contract (confirmed absent from
    to_execution_step_payload()'s output) and must not be accepted or
    stored even if present in the request body — extra keys are
    silently ignored by Pydantic's default config, which is the correct
    behavior here (not an error, just not part of this contract).
    """
    project_id = _create_project(client)
    payload = {
        "journeyId": "journey-xyz",
        "steps": [
            {
                "id": "gen-step-1",
                "type": "click",
                "selector": "#x",
                "source_step_id": "norm-step-1",
                "source_event_id": "raw-event-1",
            }
        ],
    }

    response = client.post(f"/projects/{project_id}/tests/from-execution-payload", json=payload)

    assert response.status_code == 201
    content = response.json()["content"]
    assert "source_step_id" not in content[0]
    assert "source_event_id" not in content[0]


# --- 5. resulting stored content can be passed through the existing execution path ---

def test_ingested_test_definition_can_be_executed_via_existing_path(client):
    project_id = _create_project(client)

    create_response = client.post(
        f"/projects/{project_id}/tests/from-execution-payload",
        json=INTELLIGENCE_EXECUTION_PAYLOAD,
    )
    test_id = create_response.json()["id"]

    with patch(
        "app.api.routes.test_definitions.execute_steps", return_value=_passing_result()
    ) as mock_execute:
        exec_response = client.post(f"/tests/{test_id}/execute")

    assert exec_response.status_code == 200
    assert exec_response.json()["status"] == "passed"
    # the exact stored content (with selectorKind, ids, etc.) is what
    # gets handed to the execution engine boundary, unchanged
    called_steps = mock_execute.call_args.args[0]
    assert called_steps[0]["id"] == "gen-step-nav-1"
    assert called_steps[1]["selectorKind"] == "data-testid"


# --- 6. malformed/invalid step data is rejected appropriately ---

def test_execution_payload_rejects_unknown_step_type(client):
    project_id = _create_project(client)
    payload = {
        "journeyId": "journey-bad",
        "steps": [{"id": "gen-step-1", "type": "hover", "selector": "#x"}],
    }

    response = client.post(f"/projects/{project_id}/tests/from-execution-payload", json=payload)
    assert response.status_code == 422


def test_execution_payload_rejects_missing_required_field(client):
    project_id = _create_project(client)
    # click step missing required "selector"
    payload = {
        "journeyId": "journey-bad",
        "steps": [{"id": "gen-step-1", "type": "click"}],
    }

    response = client.post(f"/projects/{project_id}/tests/from-execution-payload", json=payload)
    assert response.status_code == 422


def test_execution_payload_rejects_empty_steps(client):
    project_id = _create_project(client)
    payload = {"journeyId": "journey-empty", "steps": []}

    response = client.post(f"/projects/{project_id}/tests/from-execution-payload", json=payload)
    assert response.status_code == 422


def test_execution_payload_rejects_missing_journey_id(client):
    project_id = _create_project(client)
    payload = {"steps": INTELLIGENCE_EXECUTION_PAYLOAD["steps"]}

    response = client.post(f"/projects/{project_id}/tests/from-execution-payload", json=payload)
    assert response.status_code == 422
