"""
Tests for Execution History Stage 1: every POST /tests/{test_id}/execute
call persists a raw ExecutionRun row, without changing the existing
response contract or behavior.

Like the other route-level test files in this suite, these mock ONLY
app.api.routes.test_definitions.execute_steps -- the Execution Engine
subprocess boundary. Diagnosis and explainability are NOT mocked (they
run for real, exactly as in test_execution_diagnosis.py), since this
stage's persistence call happens independently of them and this suite
should not misrepresent that by mocking things it doesn't need to.
"""

from unittest.mock import patch

from app.models.execution_run import ExecutionRun
from app.schemas.execution import ExecutionResultOut


def _create_project(client, name="Execution History Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_test_definition(client, project_id, content=None):
    response = client.post(
        f"/projects/{project_id}/tests",
        json={
            "name": "History test",
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


# --- 1 & 2: exactly one ExecutionRun per call, pass and fail ---


def test_passing_execution_creates_exactly_one_execution_run(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    runs = db_session.query(ExecutionRun).all()
    assert len(runs) == 1


def test_failing_execution_creates_exactly_one_execution_run(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_failing_result()):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    runs = db_session.query(ExecutionRun).all()
    assert len(runs) == 1


# --- 3: correct TestDefinition reference ---


def test_execution_run_references_the_correct_test_definition(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        client.post(f"/tests/{test_id}/execute")

    run = db_session.query(ExecutionRun).one()
    assert run.test_definition_id == test_id


# --- 4: passing execution stores status="passed" ---


def test_passing_execution_stores_status_passed(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        client.post(f"/tests/{test_id}/execute")

    run = db_session.query(ExecutionRun).one()
    assert run.status == "passed"
    assert run.failed_step_id is None
    assert run.failed_step_index is None
    assert run.error is None
    assert run.evidence is None


# --- 5: failing execution stores all failure fields ---


def test_failing_execution_stores_failure_fields(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_failing_result()):
        client.post(f"/tests/{test_id}/execute")

    run = db_session.query(ExecutionRun).one()
    assert run.status == "failed"
    assert run.failed_step_id == "gen-click-1"
    assert run.failed_step_index == 1
    assert run.error == "page.click: Timeout 5000ms exceeded."
    assert run.executed_step_count == 2
    assert run.evidence is not None
    assert run.evidence["errorCategory"] == "unknown"
    assert run.evidence["failedStepId"] == "gen-click-1"


# --- 6: timing fields persisted correctly ---


def test_timing_fields_are_persisted_correctly(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_failing_result()):
        client.post(f"/tests/{test_id}/execute")

    run = db_session.query(ExecutionRun).one()
    assert run.started_at == "2026-01-01T00:00:00.000Z"
    assert run.finished_at == "2026-01-01T00:00:05.050Z"
    assert run.duration_ms == 5050
    assert run.created_at is not None  # row's own persistence timestamp


# --- 7: multiple executions create multiple distinct rows ---


def test_multiple_executions_of_same_test_definition_create_multiple_rows(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[_passing_result(), _failing_result(), _passing_result()],
    ):
        client.post(f"/tests/{test_id}/execute")
        client.post(f"/tests/{test_id}/execute")
        client.post(f"/tests/{test_id}/execute")

    runs = db_session.query(ExecutionRun).filter(ExecutionRun.test_definition_id == test_id).all()
    assert len(runs) == 3
    # distinct rows, not the same row overwritten three times
    assert len({run.id for run in runs}) == 3
    statuses = sorted(run.status for run in runs)
    assert statuses == ["failed", "passed", "passed"]


# --- 8: existing response behavior remains unchanged ---


def test_execute_response_shape_is_unchanged_by_history_persistence(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    # Every field from before this stage is still present and correct;
    # nothing about the response shape changed.
    assert body["status"] == "passed"
    assert "diagnosis" in body
    assert "explanation" in body
    assert "healing" in body
    assert "execution_run_id" not in body  # this stage adds no response field at all
    assert "run_id" not in body


# --- 9: a persistence failure does not break the execution response ---


def test_persistence_failure_does_not_break_the_execution_response(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()), patch(
        "app.api.routes.test_definitions.ExecutionRun",
        side_effect=RuntimeError("simulated persistence failure"),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    # The execution response itself must still succeed and be correct,
    # exactly as if persistence had never been attempted.
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "passed"
    assert body["diagnosis"]["has_failure"] is False

    # And genuinely nothing was persisted (construction itself failed).
    assert db_session.query(ExecutionRun).count() == 0

    # The session must remain usable afterward (rollback happened) --
    # proven by a second, normal request succeeding and persisting
    # normally.
    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        second_response = client.post(f"/tests/{test_id}/execute")
    assert second_response.status_code == 200
    assert db_session.query(ExecutionRun).count() == 1
