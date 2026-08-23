"""
Tests for Phase 5 Stage 2: GET /tests/{test_id}/analysis.

Like every other route-level test file in this suite, these mock ONLY
app.api.routes.test_definitions.execute_steps -- the Execution Engine
subprocess boundary -- when SEEDING execution history via real
POST /execute calls. Diagnosis, explainability, healing, and the
flaky-analysis engine itself are NEVER mocked: this file proves the
real Stage 1 engine, wired through the real Stage 2 Backend boundary,
against real persisted ExecutionRun history.
"""

from unittest.mock import MagicMock, patch

from app.models.execution_run import ExecutionRun
from app.schemas.execution import ExecutionResultOut


def _create_project(client, name="Flaky Analysis Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_test_definition(client, project_id, content=None):
    response = client.post(
        f"/projects/{project_id}/tests",
        json={
            "name": "Analysis test",
            "content": content
            or [
                {"id": "gen-nav-1", "type": "navigate", "url": "https://example.com"},
                {"id": "gen-click-1", "type": "click", "selector": "#submit"},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


_STEPS_WITH_DUAL_EVIDENCE = [
    {"id": "gen-nav-1", "type": "navigate", "url": "https://shop.test/"},
    {
        "id": "gen-click-1",
        "type": "click",
        "selector": "#checkout-button",
        "selectorKind": "id",
        "stableElementId": "checkout-button",
        "stableDataTestId": "checkout-submit",
    },
]

_SELECTOR_NOT_FOUND_ERROR = 'page.click: waiting for locator("#checkout-button") failed: element not found'
_TIMEOUT_ERROR = "page.click: Timeout 5000ms exceeded."


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


def _failing_result(error=_TIMEOUT_ERROR, failed_step_id="gen-click-1") -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "failed",
            "steps": [
                {"stepIndex": 0, "type": "navigate", "status": "passed", "durationMs": 50},
                {
                    "stepIndex": 1,
                    "id": failed_step_id,
                    "type": "click",
                    "status": "failed",
                    "durationMs": 10,
                    "error": error,
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
                "errorCategory": "unknown",
                "pageUrl": "https://example.com/",
                "httpStatus": None,
                "executedStepCount": 2,
                "stepDurationMs": 10,
            },
        }
    )


def _seed(client, test_id, results):
    with patch("app.api.routes.test_definitions.execute_steps", side_effect=results):
        for _ in results:
            client.post(f"/tests/{test_id}/execute")


# --- 1: GET returns analysis for a test with history ---


def test_get_returns_analysis_for_test_with_history(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_passing_result(), _passing_result(), _passing_result()])

    response = client.get(f"/tests/{test_id}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["test_definition_id"] == test_id
    assert body["executions_analyzed"] == 3


# --- 2 & 15: FAIL -> PASS -> FAIL same signature -> is_flaky=true,
#             proving correct chronological ordering through the real
#             newest-first DB query -> reversal -> engine path ---


def test_fail_pass_fail_same_signature_is_flaky(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_failing_result(), _passing_result(), _failing_result()])

    body = client.get(f"/tests/{test_id}/analysis").json()

    assert body["is_flaky"] is True
    assert body["consistently_failing"] is False
    assert len(body["recurring_signatures"]) == 1
    assert body["recurring_signatures"][0]["occurrence_count"] == 2


def test_adjacent_failures_with_no_interleaved_pass_are_not_flaky(client):
    # Proves ordering isn't accidentally inverted: two failures with NO
    # pass between them (chronologically) must not be flagged flaky.
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_failing_result(), _failing_result(), _passing_result()])

    body = client.get(f"/tests/{test_id}/analysis").json()

    assert body["is_flaky"] is False


# --- 3: FAIL -> FAIL -> FAIL -> consistently_failing=true, is_flaky=false ---


def test_all_failing_is_consistently_failing_not_flaky(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_failing_result(), _failing_result(), _failing_result()])

    body = client.get(f"/tests/{test_id}/analysis").json()

    assert body["consistently_failing"] is True
    assert body["is_flaky"] is False


# --- 4: fewer than 3 executions -> insufficient_data=true ---


def test_fewer_than_three_executions_is_insufficient_data(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_failing_result(), _passing_result()])

    body = client.get(f"/tests/{test_id}/analysis").json()

    assert body["insufficient_data"] is True
    assert body["is_flaky"] is False


# --- 5: all-pass history is not flaky ---


def test_all_passing_history_is_not_flaky(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_passing_result()] * 4)

    body = client.get(f"/tests/{test_id}/analysis").json()

    assert body["is_flaky"] is False
    assert body["consistently_failing"] is False
    assert body["passed_count"] == 4
    assert body["failed_count"] == 0


# --- 6: different failure signatures are not incorrectly merged ---


def test_different_failure_signatures_not_merged(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(
        client,
        test_id,
        [
            _failing_result(error=_TIMEOUT_ERROR),  # -> ENVIRONMENT_OR_EXECUTION
            _passing_result(),
            _failing_result(error="Request failed with status code 503"),  # -> APPLICATION_BUG
        ],
    )

    body = client.get(f"/tests/{test_id}/analysis").json()

    # Different classifications for the same step = different
    # signatures; neither recurred, so not flaky.
    assert body["is_flaky"] is False
    assert body["recurring_signatures"] == []


# --- 7: diagnosis classification counts are correct ---


def test_diagnosis_classification_counts_are_correct(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(
        client,
        test_id,
        [
            _failing_result(error=_TIMEOUT_ERROR),
            _failing_result(error=_TIMEOUT_ERROR),
            _failing_result(error="Request failed with status code 503"),
        ],
    )

    body = client.get(f"/tests/{test_id}/analysis").json()

    assert body["diagnosis_classification_counts"] == {
        "ENVIRONMENT_OR_EXECUTION": 2,
        "APPLICATION_BUG": 1,
    }


# --- 8 & 9: healing statistics are correct; successful healing does
#            NOT convert an original failure into a pass ---


def test_healing_statistics_and_original_failure_status_are_preserved(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_DUAL_EVIDENCE)

    healed_success = _passing_result()
    # Two full execute() cycles: each seeds ONE ExecutionRun, but
    # execute_steps is called twice internally per cycle (original +
    # healing attempt) since the content has real dual-identifier
    # evidence and a selector-not-found-style error.
    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[
            _failing_result(error=_SELECTOR_NOT_FOUND_ERROR),
            healed_success,
            _failing_result(error=_SELECTOR_NOT_FOUND_ERROR),
            healed_success,
            _passing_result(),
        ],
    ):
        client.post(f"/tests/{test_id}/execute")  # run 1: fails, heals successfully
        client.post(f"/tests/{test_id}/execute")  # run 2: fails, heals successfully
        client.post(f"/tests/{test_id}/execute")  # run 3: passes outright

    body = client.get(f"/tests/{test_id}/analysis").json()

    # Original status drives pass/fail counts -- both healed runs still
    # count as FAILURES, never converted into passes by healing.
    assert body["failed_count"] == 2
    assert body["passed_count"] == 1
    assert body["healing_attempted_count"] == 2
    assert body["healing_succeeded_count"] == 2
    assert body["healing_failed_count"] == 0


# --- 10 & 14: default window is 20; more than N only analyzes newest N ---


def test_default_window_is_20_and_excludes_older_executions(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    # 21 executions: the oldest one is a failure with a UNIQUE
    # signature that must NOT be visible once the default window (20)
    # excludes it.
    results = [_failing_result(error="Request failed with status code 503")]
    results += [_passing_result()] * 20
    _seed(client, test_id, results)

    body = client.get(f"/tests/{test_id}/analysis").json()

    assert body["executions_analyzed"] == 20
    assert body["failed_count"] == 0  # the oldest (excluded) failure is invisible
    assert body["passed_count"] == 20


# --- 11 & 13: custom ?window=N works; smaller histories analyze all
#              available rows ---


def test_custom_window_query_param_limits_analysis(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_passing_result()] * 8)

    body = client.get(f"/tests/{test_id}/analysis?window=5").json()

    assert body["executions_analyzed"] == 5


def test_window_larger_than_available_history_analyzes_all(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_passing_result(), _passing_result(), _passing_result()])

    body = client.get(f"/tests/{test_id}/analysis?window=20").json()

    assert body["executions_analyzed"] == 3
    assert body["insufficient_data"] is False


# --- 12: invalid window below 3 is rejected ---


def test_window_below_three_is_rejected(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    response = client.get(f"/tests/{test_id}/analysis?window=2")

    assert response.status_code == 422


# --- 16: empty history for an existing TestDefinition -> valid
#         insufficient_data result, not 404 ---


def test_empty_history_returns_valid_insufficient_data_result(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)  # never executed

    response = client.get(f"/tests/{test_id}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_data"] is True
    assert body["executions_analyzed"] == 0
    assert body["is_flaky"] is False


# --- 17: nonexistent TestDefinition follows the existing 404 convention ---


def test_nonexistent_test_definition_returns_404(client):
    response = client.get("/tests/does-not-exist/analysis")
    assert response.status_code == 404


# --- 18: endpoint is read-only ---


def test_endpoint_does_not_create_or_modify_execution_run_rows(client, db_session):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_passing_result(), _passing_result(), _passing_result()])

    count_before = db_session.query(ExecutionRun).count()
    client.get(f"/tests/{test_id}/analysis")
    client.get(f"/tests/{test_id}/analysis")
    count_after = db_session.query(ExecutionRun).count()

    assert count_before == count_after == 3


# --- 19, 20, 21: endpoint never calls execute_steps, diagnose_and_explain,
#                 or healing ---


def test_analysis_endpoint_never_triggers_execution_diagnosis_or_healing(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    _seed(client, test_id, [_passing_result(), _passing_result(), _passing_result()])

    with patch(
        "app.api.routes.test_definitions.execute_steps", new=MagicMock()
    ) as mock_execute, patch(
        "app.api.routes.test_definitions.diagnose_and_explain", new=MagicMock()
    ) as mock_diagnose, patch(
        "app.api.routes.test_definitions.prepare_healing_attempt", new=MagicMock()
    ) as mock_heal:
        response = client.get(f"/tests/{test_id}/analysis")

    assert response.status_code == 200
    mock_execute.assert_not_called()
    mock_diagnose.assert_not_called()
    mock_heal.assert_not_called()


# --- 22: existing /execute response remains unchanged ---


def test_execute_response_unchanged_by_the_new_analysis_endpoint(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=_passing_result()):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "status",
        "steps",
        "failedStepIndex",
        "failedStepId",
        "error",
        "executedStepCount",
        "startedAt",
        "finishedAt",
        "durationMs",
        "evidence",
        "diagnosis",
        "explanation",
        "healing",
    }
    assert "analysis" not in body
