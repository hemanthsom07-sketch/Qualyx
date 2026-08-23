"""
Tests for Execution History Stage 4: GET /tests/{test_id}/executions,
a read-only endpoint exposing the ExecutionRun history persisted by
Stages 1-3 (raw execution result, diagnosis, explanation, healing).

Separate from test_execution_history.py (which covers the WRITE path --
Stages 1-3's persistence behavior on POST /execute) since this file
covers the READ path only, following this codebase's existing
convention of one focused file per concern rather than growing a single
large file indefinitely.

Setup executions are created via real POST /execute calls (mocking only
execute_steps, exactly like every other test file in this suite) so
that what's being read back is genuinely what Stages 1-3 persisted --
not a hand-inserted row that might not match the real contract.
"""

from unittest.mock import MagicMock, patch

from app.schemas.execution import ExecutionResultOut


def _create_project(client, name="Execution History Retrieval Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_test_definition(client, project_id, content=None):
    response = client.post(
        f"/projects/{project_id}/tests",
        json={
            "name": "Retrieval test",
            "content": content
            or [
                {"id": "gen-nav-1", "type": "navigate", "url": "https://example.com"},
                {"id": "gen-click-1", "type": "click", "selector": "#submit"},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _passing_result() -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "passed",
            "steps": [
                {"stepIndex": 0, "type": "navigate", "status": "passed", "durationMs": 50},
                {"stepIndex": 1, "id": "gen-click-1", "type": "click", "status": "passed", "durationMs": 10},
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


def _failing_result() -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "failed",
            "steps": [
                {"stepIndex": 0, "type": "navigate", "status": "passed", "durationMs": 50},
                {
                    "stepIndex": 1,
                    "id": "gen-click-1",
                    "type": "click",
                    "status": "failed",
                    "durationMs": 5000,
                    "error": "page.click: Timeout 5000ms exceeded.",
                },
            ],
            "failedStepIndex": 1,
            "failedStepId": "gen-click-1",
            "error": "page.click: Timeout 5000ms exceeded.",
            "executedStepCount": 2,
            "startedAt": "2026-01-01T00:00:00.000Z",
            "finishedAt": "2026-01-01T00:00:05.050Z",
            "durationMs": 5050,
            "evidence": {
                "failedStepId": "gen-click-1",
                "failedStepIndex": 1,
                "stepType": "click",
                "action": {"selector": "#submit"},
                "errorMessage": "page.click: Timeout 5000ms exceeded.",
                "errorCategory": "unknown",
                "pageUrl": "https://example.com/",
                "httpStatus": None,
                "executedStepCount": 2,
                "stepDurationMs": 5000,
            },
        }
    )


# --- 1: GET returns execution history for the requested TestDefinition ---


def test_get_returns_execution_history_for_the_test_definition(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        client.post(f"/tests/{test_id}/execute")

    response = client.get(f"/tests/{test_id}/executions")

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["test_definition_id"] == test_id


# --- 2: multiple executions are returned independently ---


def test_multiple_executions_are_returned_independently(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[_passing_result(), _failing_result(), _passing_result()],
    ):
        client.post(f"/tests/{test_id}/execute")
        client.post(f"/tests/{test_id}/execute")
        client.post(f"/tests/{test_id}/execute")

    runs = client.get(f"/tests/{test_id}/executions").json()

    assert len(runs) == 3
    assert len({run["id"] for run in runs}) == 3  # genuinely distinct rows
    statuses = sorted(run["status"] for run in runs)
    assert statuses == ["failed", "passed", "passed"]


# --- 3: deterministic order (newest-first, matching the existing
#        GET /projects/{project_id}/tests convention) ---


def test_executions_are_returned_newest_first(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[_passing_result(), _failing_result()],
    ):
        first_response = client.post(f"/tests/{test_id}/execute")
        second_response = client.post(f"/tests/{test_id}/execute")

    runs = client.get(f"/tests/{test_id}/executions").json()

    assert len(runs) == 2
    # The second (failing) execution was persisted after the first
    # (passing) one, so newest-first means it must come first.
    assert runs[0]["status"] == "failed"
    assert runs[1]["status"] == "passed"


# --- 4, 5, 6: stored diagnosis/explanation/healing are returned ---


def test_stored_diagnosis_explanation_and_healing_are_returned(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_failing_result()):
        client.post(f"/tests/{test_id}/execute")

    run = client.get(f"/tests/{test_id}/executions").json()[0]

    assert run["diagnosis"]["has_failure"] is True
    assert run["diagnosis"]["classification"] is not None
    assert run["explanation"]["has_failure"] is True
    assert run["explanation"]["headline"] != "Execution passed"
    assert run["healing"] is not None
    assert run["healing"]["status"] in (
        "not_eligible",
        "no_candidate",
        "rejected",
        "healed",
        "healing_failed",
    )


# --- 7: failure/evidence information is returned ---


def test_failure_and_evidence_information_is_returned(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_failing_result()):
        client.post(f"/tests/{test_id}/execute")

    run = client.get(f"/tests/{test_id}/executions").json()[0]

    assert run["failed_step_id"] == "gen-click-1"
    assert run["failed_step_index"] == 1
    assert run["error"] == "page.click: Timeout 5000ms exceeded."
    assert run["evidence"] is not None
    assert run["evidence"]["errorCategory"] == "unknown"


# --- 8: empty history returns the correct empty response ---


def test_empty_history_returns_empty_list(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    # Never executed.

    response = client.get(f"/tests/{test_id}/executions")

    assert response.status_code == 200
    assert response.json() == []


# --- 9: nonexistent TestDefinition returns the existing 404 behavior ---


def test_nonexistent_test_definition_returns_404(client):
    response = client.get("/tests/does-not-exist/executions")
    assert response.status_code == 404


# --- 10, 11, 12: the endpoint does not trigger execution, diagnosis,
#                 or healing ---


def test_get_history_never_triggers_execution_diagnosis_or_healing(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    # Seed one real execution first (execute_steps mocked only for setup).
    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        client.post(f"/tests/{test_id}/execute")

    # Now hit the read-only history endpoint with execution/diagnosis/
    # healing all replaced by bare mocks -- none of them must be called.
    with patch(
        "app.api.routes.test_definitions.execute_steps", new=MagicMock()
    ) as mock_execute, patch(
        "app.api.routes.test_definitions.diagnose_and_explain", new=MagicMock()
    ) as mock_diagnose, patch(
        "app.api.routes.test_definitions.prepare_healing_attempt", new=MagicMock()
    ) as mock_heal:
        response = client.get(f"/tests/{test_id}/executions")

    assert response.status_code == 200
    assert len(response.json()) == 1  # the earlier seeded run is still visible
    mock_execute.assert_not_called()
    mock_diagnose.assert_not_called()
    mock_heal.assert_not_called()


# --- 13: existing API behavior remains unchanged ---


def test_existing_endpoints_remain_unaffected_by_the_new_history_route(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    # GET /tests/{id} (existing) still works.
    get_response = client.get(f"/tests/{test_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == test_id

    # POST /execute (existing) still works and is unaffected by the new
    # sibling route existing.
    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        execute_response = client.post(f"/tests/{test_id}/execute")
    assert execute_response.status_code == 200
    assert "healing" in execute_response.json()

    # GET /projects/{id}/tests (existing) still works.
    list_response = client.get(f"/projects/{project_id}/tests")
    assert list_response.status_code == 200
