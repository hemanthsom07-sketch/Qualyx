"""
Tests for POST /tests/{test_id}/execute.

These mock app.services.execution_client.execute_steps rather than
actually spawning the Node execution engine, so the Python test suite
stays independently runnable (no Node/Playwright dependency in the
backend's own test environment). The subprocess boundary itself is
covered separately by the execution-engine's own stdin-runner tests
(tests/stdin-runner.test.ts), which do spawn the real process.
"""

from unittest.mock import patch

from app.schemas.execution import ExecutionResultOut
from app.services.execution_client import ExecutionEngineError, ExecutionValidationError

STEP_CONTENT = [
    {"type": "navigate", "url": "https://example.com"},
    {"type": "click", "selector": "#submit"},
]


def _create_project(client, name="Execution Test Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_test_definition(client, project_id, content=None):
    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Executable test", "content": content or STEP_CONTENT},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _passing_result() -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "passed",
            "steps": [
                {"stepIndex": 0, "type": "navigate", "status": "passed", "durationMs": 50},
                {"stepIndex": 1, "type": "click", "status": "passed", "durationMs": 30},
            ],
            "failedStepIndex": None,
            "failedStepId": None,
            "error": None,
            "executedStepCount": 2,
            "startedAt": "2026-01-01T00:00:00.000Z",
            "finishedAt": "2026-01-01T00:00:00.100Z",
            "durationMs": 100,
        }
    )


def _failing_result(failed_step_id=None) -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "failed",
            "steps": [
                {"stepIndex": 0, "type": "navigate", "status": "passed", "durationMs": 50},
                {
                    "stepIndex": 1,
                    "type": "click",
                    "status": "failed",
                    "durationMs": 5000,
                    "error": "page.click: Timeout 5000ms exceeded.",
                    **({"id": failed_step_id} if failed_step_id else {}),
                },
            ],
            "failedStepIndex": 1,
            "failedStepId": failed_step_id,
            "error": "page.click: Timeout 5000ms exceeded.",
            "executedStepCount": 2,
            "startedAt": "2026-01-01T00:00:00.000Z",
            "finishedAt": "2026-01-01T00:00:05.050Z",
            "durationMs": 5050,
        }
    )


def test_execute_existing_test_definition_successfully(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps", return_value=_passing_result()
    ) as mock_execute:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "passed"
    assert body["failedStepIndex"] is None
    assert body["failedStepId"] is None
    assert body["error"] is None
    assert body["executedStepCount"] == 2
    mock_execute.assert_called_once()
    called_steps = mock_execute.call_args.args[0]
    assert called_steps == STEP_CONTENT


def test_execute_missing_test_definition_returns_404(client):
    response = client.post("/tests/does-not-exist/execute")
    assert response.status_code == 404


def test_execute_reports_failed_status_and_failed_step_index(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_failing_result()):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["failedStepIndex"] == 1
    assert body["failedStepId"] is None
    assert body["error"] == "page.click: Timeout 5000ms exceeded."
    assert body["executedStepCount"] == 2
    # fail-fast: only the attempted steps are present
    assert len(body["steps"]) == 2


def test_execute_invalid_steps_returns_422(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=ExecutionValidationError("Step 0: unknown step type \"hover\""),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 422
    assert "hover" in response.json()["detail"]


def test_execute_engine_failure_returns_502(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=ExecutionEngineError("Execution engine timed out after 30s"),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 502


# --- Task 8: stable step ID propagation through the API response ---

def test_execute_response_accepts_and_returns_failed_step_id(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(
        client,
        project_id,
        content=[
            {"id": "gen-nav-1", "type": "navigate", "url": "https://example.com"},
            {"id": "gen-click-abc", "type": "click", "selector": "#submit"},
        ],
    )

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(failed_step_id="gen-click-abc"),
    ) as mock_execute:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["failedStepId"] == "gen-click-abc"
    assert body["failedStepIndex"] == 1
    # the id was preserved through storage and forwarded to the engine call
    called_steps = mock_execute.call_args.args[0]
    assert called_steps[1]["id"] == "gen-click-abc"


def test_execute_successful_run_returns_null_failed_step_id_even_with_ids_present(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(
        client,
        project_id,
        content=[{"id": "gen-nav-1", "type": "navigate", "url": "https://example.com"}],
    )

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    assert response.json()["failedStepId"] is None


def test_execute_failure_without_id_returns_null_failed_step_id(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)  # STEP_CONTENT has no ids

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_failing_result()):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    assert response.json()["failedStepId"] is None


def test_create_test_definition_preserves_step_id(client):
    project_id = _create_project(client)
    response = client.post(
        f"/projects/{project_id}/tests",
        json={
            "name": "With stable ids",
            "content": [{"id": "gen-nav-1", "type": "navigate", "url": "https://example.com"}],
        },
    )
    assert response.status_code == 201
    assert response.json()["content"][0]["id"] == "gen-nav-1"


def test_create_test_definition_without_id_does_not_store_null_id(client):
    project_id = _create_project(client)
    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "No ids", "content": STEP_CONTENT},
    )
    assert response.status_code == 201
    # backward compatibility: old-shape content has no "id" key at all,
    # not an explicit null
    assert "id" not in response.json()["content"][0]
