"""
Tests for Milestone 2A: POST /tests/{test_id}/execute now returns
`diagnosis` and `explanation` alongside the existing execution result.

Like test_execution.py, these mock app.api.routes.test_definitions.execute_steps
rather than spawning the real Execution Engine subprocess. Diagnosis and
explainability themselves are NOT re-tested here (that's
intelligence/tests/test_failure_diagnosis.py and
intelligence/tests/test_explainability.py's job) -- these tests only
confirm the wiring: that the real diagnose_execution_result()/
explain_diagnosis() functions are actually invoked with correctly
translated inputs, and that their real output reaches the API response
unaltered.
"""

from unittest.mock import patch

from app.schemas.execution import ExecutionResultOut


def _create_project(client, name="Diagnosis Wiring Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_test_definition(client, project_id, content):
    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Diagnosable test", "content": content},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _passing_result() -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "passed",
            "steps": [
                {"stepIndex": 0, "type": "navigate", "status": "passed", "durationMs": 50},
            ],
            "failedStepIndex": None,
            "failedStepId": None,
            "error": None,
            "executedStepCount": 1,
            "startedAt": "2026-01-01T00:00:00.000Z",
            "finishedAt": "2026-01-01T00:00:00.100Z",
            "durationMs": 100,
            "evidence": None,
        }
    )


def _failing_result(failed_step_id, error, error_category="unknown") -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "failed",
            "steps": [
                {"stepIndex": 0, "type": "navigate", "status": "passed", "durationMs": 50},
                {
                    "stepIndex": 1,
                    "type": "click",
                    "status": "failed",
                    "durationMs": 10,
                    "error": error,
                    **({"id": failed_step_id} if failed_step_id else {}),
                },
            ],
            "failedStepIndex": 1,
            "failedStepId": failed_step_id,
            "error": error,
            "executedStepCount": 2,
            "startedAt": "2026-01-01T00:00:00.000Z",
            "finishedAt": "2026-01-01T00:00:00.100Z",
            "durationMs": 100,
            "evidence": {
                "failedStepId": failed_step_id,
                "failedStepIndex": 1,
                "stepType": "click",
                "action": {"selector": "#submit"},
                "errorMessage": error,
                "errorCategory": error_category,
                "pageUrl": "https://example.com/",
                "httpStatus": None,
                "executedStepCount": 2,
                "stepDurationMs": 10,
            },
        }
    )


_STEPS_WITH_IDS = [
    {"id": "gen-nav-1", "type": "navigate", "url": "https://example.com"},
    {"id": "gen-click-1", "type": "click", "selector": "#submit"},
]

_STEPS_WITHOUT_IDS = [
    {"type": "navigate", "url": "https://example.com"},
    {"type": "click", "selector": "#submit"},
]


# --- A. Successful execution ---


def test_successful_execution_reports_no_failure_and_passed_headline(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_IDS)

    with patch(
        "app.api.routes.test_definitions.execute_steps", return_value=_passing_result()
    ):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "passed"  # existing execution field, unchanged

    assert body["diagnosis"]["has_failure"] is False
    assert body["diagnosis"]["classification"] is None

    assert body["explanation"]["has_failure"] is False
    assert body["explanation"]["classification"] is None
    assert body["explanation"]["headline"] == "Execution passed"


# --- B. Application failure (HTTP 5xx pattern) ---


def test_application_failure_classified_as_application_bug(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_IDS)

    result = _failing_result(
        failed_step_id="gen-click-1",
        error="Request failed with status code 503",
    )

    with patch("app.api.routes.test_definitions.execute_steps", return_value=result):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "failed"  # existing execution field, unchanged
    assert body["failedStepId"] == "gen-click-1"  # existing execution field, unchanged

    assert body["diagnosis"]["classification"] == "APPLICATION_BUG"
    assert body["diagnosis"]["correlation_established"] is True
    assert body["diagnosis"]["generated_step_id"] == "gen-click-1"

    assert body["explanation"]["classification"] == "APPLICATION_BUG"
    assert body["explanation"]["headline"] == "Likely an application bug"
    assert body["explanation"]["confidence"] == body["diagnosis"]["confidence"]


# --- C. Unknown/uncertain failure ---


def test_unrecognized_error_text_remains_uncertain(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_IDS)

    result = _failing_result(
        failed_step_id="gen-click-1",
        error="Something unexpected happened",
    )

    with patch("app.api.routes.test_definitions.execute_steps", return_value=result):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()

    assert body["diagnosis"]["classification"] == "UNCERTAIN"
    assert body["explanation"]["classification"] == "UNCERTAIN"
    assert body["explanation"]["headline"] == "Cause is uncertain"
    # No fabricated provenance for an unmatched-pattern failure either.
    assert body["diagnosis"]["source_step_id"] is None
    assert body["diagnosis"]["source_event_id"] is None


def test_uncorrelated_failure_forced_uncertain_with_no_fabricated_step_id(client):
    # failedStepId is None -- correlation cannot be established, and per
    # diagnosis's own contract this must be forced to UNCERTAIN regardless
    # of the error text, rather than guessing a classification.
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_IDS)

    result = _failing_result(
        failed_step_id=None,
        error="Request failed with status code 503",  # would otherwise match APPLICATION_BUG
    )

    with patch("app.api.routes.test_definitions.execute_steps", return_value=result):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()

    assert body["diagnosis"]["classification"] == "UNCERTAIN"
    assert body["diagnosis"]["correlation_established"] is False
    assert body["diagnosis"]["generated_step_id"] is None
    assert body["diagnosis"]["source_step_id"] is None
    assert body["diagnosis"]["source_event_id"] is None


# --- D. Provenance: never fabricated when unavailable ---


def test_source_provenance_is_always_none_since_stored_content_never_has_it(client):
    # TestDefinition.content (regardless of how it was created) never
    # contains source_step_id/source_event_id -- confirmed absent from
    # both TestDefinitionCreate and ExecutionPayloadCreate schemas.
    # Diagnosis must reflect that honestly as null, never fabricate a
    # value for it.
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_IDS)

    result = _failing_result(
        failed_step_id="gen-click-1",
        error="Request failed with status code 503",
    )

    with patch("app.api.routes.test_definitions.execute_steps", return_value=result):
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    # Correlation succeeded (generated_step_id is set), but provenance
    # fields specifically remain null.
    assert body["diagnosis"]["generated_step_id"] == "gen-click-1"
    assert body["diagnosis"]["source_step_id"] is None
    assert body["diagnosis"]["source_event_id"] is None


def test_steps_without_stored_ids_cannot_be_correlated_and_report_null_ids(client):
    # A TestDefinition created without any step ids at all (legacy
    # create_test_definition path, no "id" key present) must not have
    # ids fabricated for correlation purposes.
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITHOUT_IDS)

    result = _failing_result(failed_step_id=None, error="Timeout 5000ms exceeded")

    with patch("app.api.routes.test_definitions.execute_steps", return_value=result):
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    assert body["diagnosis"]["correlation_established"] is False
    assert body["diagnosis"]["generated_step_id"] is None
    assert body["diagnosis"]["source_step_id"] is None
    assert body["diagnosis"]["source_event_id"] is None


# --- E. Existing invalid-execution behavior remains intact ---


def test_invalid_steps_still_returns_422_without_diagnosis_fields(client):
    from app.services.execution_client import ExecutionValidationError

    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_IDS)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=ExecutionValidationError('Step 0: unknown step type "hover"'),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 422
    assert "hover" in response.json()["detail"]
    assert "diagnosis" not in response.json()


def test_engine_failure_still_returns_502_without_diagnosis_fields(client):
    from app.services.execution_client import ExecutionEngineError

    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_IDS)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=ExecutionEngineError("Execution engine timed out after 30s"),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 502
    assert "diagnosis" not in response.json()


def test_missing_test_definition_still_returns_404(client):
    response = client.post("/tests/does-not-exist/execute")
    assert response.status_code == 404
