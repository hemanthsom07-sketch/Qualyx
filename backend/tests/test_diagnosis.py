"""
Tests for the Backend -> Intelligence diagnosis bridge, wired into
POST /tests/{test_id}/execute.

Two layers of verification exist for this bridge:

1. These tests, which mock app.api.routes.test_definitions.diagnose
   (the boundary function) to verify the ROUTE's wiring: is diagnose()
   called only on failure, is its result correctly attached as the
   additive `diagnosis` field, is the response shape otherwise
   unchanged. This mirrors the existing pattern of mocking
   execute_steps() in test_execution.py, for the same reason: the
   Python test suite must stay runnable without a live Node/Playwright
   process AND without the real `intelligence` package necessarily
   being importable from wherever pytest happens to run.

2. app/services/diagnosis_client.py's actual conversion logic (building
   LocalGeneratedTest from TestDefinition.content, converting
   ExecutionResultOut into Intelligence's ExecutionResult/FailureEvidence
   dataclasses, and calling the REAL diagnose_execution_result()) was
   separately verified against the real, uploaded Intelligence source
   for intelligence/diagnosis/execution_result.py,
   intelligence/diagnosis/failure_diagnosis.py,
   intelligence/test_generation/generated_test.py, and
   intelligence/test_generation/execution_payload.py — confirming
   correlated failures, null-failedStepId, and unknown-failedStepId all
   produce the real, actual UNCERTAIN/correlated behavior Intelligence's
   own code determines, with source_step_id/source_event_id always None
   and never fabricated. That verification could not run inside this
   Python test suite itself (diagnosis_client.py's own imports need
   sqlalchemy/pydantic, unavailable in the sandbox this bridge was
   authored in) — it is not duplicated as a pytest test here to avoid
   silently asserting behavior this suite cannot actually exercise;
   see the implementation report for the full verification transcript.
"""

from unittest.mock import patch

from app.schemas.execution import DiagnosisOut, ExecutionResultOut

STEP_CONTENT_WITH_IDS = [
    {"id": "gen-step-nav-1", "type": "navigate", "url": "https://example.com"},
    {"id": "gen-step-click-2", "type": "click", "selector": "#submit"},
]


def _create_project(client, name="Diagnosis Bridge Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_test_definition(client, project_id, content=None):
    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Diagnosable test", "content": content or STEP_CONTENT_WITH_IDS},
    )
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


def _failing_result(failed_step_id="gen-step-click-2", error_category="selector") -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "failed",
            "steps": [
                {"stepIndex": 0, "id": "gen-step-nav-1", "type": "navigate", "status": "passed", "durationMs": 50},
                {
                    "stepIndex": 1,
                    "id": failed_step_id,
                    "type": "click",
                    "status": "failed",
                    "durationMs": 5000,
                    "error": "page.click: Timeout 5000ms exceeded.",
                },
            ],
            "failedStepIndex": 1,
            "failedStepId": failed_step_id,
            "error": "page.click: Timeout 5000ms exceeded.",
            "executedStepCount": 2,
            "startedAt": "2026-01-01T00:00:00.000Z",
            "finishedAt": "2026-01-01T00:00:05.050Z",
            "durationMs": 5050,
            "evidence": {
                "failedStepId": failed_step_id,
                "failedStepIndex": 1,
                "stepType": "click",
                "action": {"selector": "#submit"},
                "errorMessage": "page.click: Timeout 5000ms exceeded.",
                "errorCategory": error_category,
                "pageUrl": "https://example.com/",
                "httpStatus": None,
                "executedStepCount": 2,
                "stepDurationMs": 5000,
            },
        }
    )


def _correlated_diagnosis() -> DiagnosisOut:
    return DiagnosisOut.model_validate(
        {
            "hasFailure": True,
            "classification": "ENVIRONMENT_OR_EXECUTION",
            "confidence": 0.55,
            "correlationEstablished": True,
            "failedStepId": "gen-step-click-2",
            "failedStepIndex": 1,
            "error": "page.click: Timeout 5000ms exceeded.",
            "generatedStepId": "gen-step-click-2",
            "sourceStepId": None,
            "sourceEventId": None,
            "evidence": ["Execution failed at step 'gen-step-click-2' (type: click), correlated via failedStepId."],
            "explanation": "The failure text matches a timeout/network-type pattern.",
        }
    )


def _uncertain_uncorrelated_diagnosis(failed_step_id=None) -> DiagnosisOut:
    return DiagnosisOut.model_validate(
        {
            "hasFailure": True,
            "classification": "UNCERTAIN",
            "confidence": 0.1,
            "correlationEstablished": False,
            "failedStepId": failed_step_id,
            "failedStepIndex": 1,
            "error": "some failure",
            "generatedStepId": None,
            "sourceStepId": None,
            "sourceEventId": None,
            "evidence": ["Execution status was 'failed', but the failed step could not be correlated."],
            "explanation": "No matching stable step id was available.",
        }
    )


# --- 1. successful execution produces no diagnosis ---

def test_passing_execution_does_not_invoke_diagnosis(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps", return_value=_passing_result()
    ), patch("app.api.routes.test_definitions.diagnose") as mock_diagnose:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "passed"
    assert body["diagnosis"] is None
    mock_diagnose.assert_not_called()


# --- 2. a correlated execution failure reaches the existing diagnosis layer ---

def test_correlated_failure_invokes_diagnosis_and_attaches_result(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(failed_step_id="gen-step-click-2"),
    ), patch(
        "app.api.routes.test_definitions.diagnose", return_value=_correlated_diagnosis()
    ) as mock_diagnose:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    mock_diagnose.assert_called_once()
    # diagnose() is called with (test_definition, execution_result) -- both real objects
    called_args = mock_diagnose.call_args.args
    assert called_args[0].id == test_id
    assert called_args[1].status == "failed"

    diagnosis = body["diagnosis"]
    assert diagnosis is not None
    assert diagnosis["correlationEstablished"] is True
    assert diagnosis["generatedStepId"] == "gen-step-click-2"
    assert diagnosis["classification"] == "ENVIRONMENT_OR_EXECUTION"


# --- 3 & 4. uncorrelated failures (null and unknown failedStepId) preserve
#            Intelligence's existing UNCERTAIN contract, not fabricated ---

def test_failure_with_null_failed_step_id_preserves_uncertain_contract(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(failed_step_id=None),
    ), patch(
        "app.api.routes.test_definitions.diagnose",
        return_value=_uncertain_uncorrelated_diagnosis(failed_step_id=None),
    ) as mock_diagnose:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    diagnosis = response.json()["diagnosis"]
    assert diagnosis["correlationEstablished"] is False
    assert diagnosis["classification"] == "UNCERTAIN"
    assert diagnosis["failedStepId"] is None
    assert diagnosis["generatedStepId"] is None
    mock_diagnose.assert_called_once()


def test_failure_with_unknown_failed_step_id_preserves_uncertain_contract(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(failed_step_id="does-not-exist-in-generated-test"),
    ), patch(
        "app.api.routes.test_definitions.diagnose",
        return_value=_uncertain_uncorrelated_diagnosis(failed_step_id="does-not-exist-in-generated-test"),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    diagnosis = response.json()["diagnosis"]
    assert diagnosis["correlationEstablished"] is False
    assert diagnosis["classification"] == "UNCERTAIN"
    # failedStepId is passed through verbatim (supplementary/informational),
    # but never treated as a successful correlation
    assert diagnosis["failedStepId"] == "does-not-exist-in-generated-test"
    assert diagnosis["generatedStepId"] is None


# --- 5. nested evidence.errorCategory remains nested, never top-level ---

def test_evidence_error_category_remains_nested_alongside_diagnosis(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(error_category="network"),
    ), patch("app.api.routes.test_definitions.diagnose", return_value=_correlated_diagnosis()):
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    assert "errorCategory" not in body  # never top-level
    assert body["evidence"]["errorCategory"] == "network"  # only nested


# --- 6. source_step_id/source_event_id are never fabricated ---

def test_diagnosis_never_fabricates_provenance(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(),
    ), patch("app.api.routes.test_definitions.diagnose", return_value=_correlated_diagnosis()):
        response = client.post(f"/tests/{test_id}/execute")

    diagnosis = response.json()["diagnosis"]
    assert diagnosis["sourceStepId"] is None
    assert diagnosis["sourceEventId"] is None


# --- 7. existing execution behavior remains intact ---

def test_execute_404_and_422_paths_unaffected_by_diagnosis_bridge(client):
    response = client.post("/tests/does-not-exist/execute")
    assert response.status_code == 404


def test_execute_engine_error_path_unaffected_by_diagnosis_bridge(client):
    from app.services.execution_client import ExecutionEngineError

    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=ExecutionEngineError("boom"),
    ), patch("app.api.routes.test_definitions.diagnose") as mock_diagnose:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 502
    mock_diagnose.assert_not_called()
