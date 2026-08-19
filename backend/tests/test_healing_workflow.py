"""
Tests for Phase 4 Stage E: POST /tests/{test_id}/execute now attempts
healing on a failed execution and returns a `healing` field alongside
the existing execution/diagnosis/explanation fields.

These mock ONLY app.api.routes.test_definitions.execute_steps -- the
Execution Engine subprocess boundary -- exactly like every other test
file in this suite (test_execution.py, test_execution_diagnosis.py,
test_recordings.py). Diagnosis, explainability, and healing itself are
NOT mocked: diagnose_execution_result(), explain_diagnosis(),
determine_eligibility(), propose_healing(), and apply_healing() all run
for real, against real stored TestDefinition content. These tests only
confirm the wiring: that a real diagnosed failure correctly triggers
(or correctly does not trigger) a real healing attempt, that a second
real execute_steps() call happens with the real healed steps when
appropriate, and that the real second result is reported accurately.
"""

from unittest.mock import patch

from app.schemas.execution import ExecutionResultOut


def _create_project(client, name="Healing Integration Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_test_definition(client, project_id, content):
    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Healable test", "content": content},
    )
    assert response.status_code == 201
    return response.json()["id"]


# A step with a genuine dual-identifier evidence: primary selector uses
# the HTML id, but a data-testid was also genuinely known for the same
# element (Phase 4 selector-evidence milestone) -- this is exactly the
# shape healing needs to find a real, non-fabricated candidate.
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

# A step with only ONE known identifier -- genuinely no second piece of
# evidence exists, so healing must honestly report no_candidate.
_STEPS_WITH_SINGLE_EVIDENCE = [
    {"id": "gen-nav-1", "type": "navigate", "url": "https://shop.test/"},
    {
        "id": "gen-click-1",
        "type": "click",
        "selector": "#checkout-button",
        "selectorKind": "id",
        "stableElementId": "checkout-button",
        # no stableDataTestId -- genuinely unknown
    },
]


def _passing_result(steps=None) -> ExecutionResultOut:
    return ExecutionResultOut.model_validate(
        {
            "status": "passed",
            "steps": steps
            or [
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


def _failing_result(failed_step_id, error) -> ExecutionResultOut:
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
                "action": {"selector": "#checkout-button"},
                "errorMessage": error,
                "errorCategory": "unknown",
                "pageUrl": "https://shop.test/",
                "httpStatus": None,
                "executedStepCount": 2,
                "stepDurationMs": 10,
            },
        }
    )


_SELECTOR_NOT_FOUND_ERROR = 'page.click: waiting for locator("#checkout-button") failed: element not found'


# --- 1-8: the full successful healing cycle ---


def test_successful_healing_cycle_reports_healed_and_calls_execute_steps_twice(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_DUAL_EVIDENCE)

    original_failure = _failing_result("gen-click-1", _SELECTOR_NOT_FOUND_ERROR)
    healed_success = _passing_result()

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[original_failure, healed_success],
    ) as mock_execute:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()

    # 1. original execution fails -- reflected in the top-level fields, unchanged
    assert body["status"] == "failed"
    assert body["failedStepId"] == "gen-click-1"

    # 2. real diagnosis ran
    assert body["diagnosis"]["classification"] == "UNCERTAIN"
    assert body["diagnosis"]["correlation_established"] is True

    # 3-6: real eligibility/candidate/application produced a real proposal,
    # and a genuine second execution happened
    healing = body["healing"]
    assert healing["status"] == "healed"
    assert healing["applied"] is True
    assert healing["original_selector"] == "#checkout-button"
    assert healing["proposed_selector"] == '[data-testid="checkout-submit"]'
    assert healing["proposed_selector_kind"] == "data-testid"

    # 7. healed_execution nested result reflects the second (successful) run
    assert healing["healed_execution"]["status"] == "passed"

    # exactly two execute_steps calls: original + one healing attempt
    assert mock_execute.call_count == 2
    first_call_steps = mock_execute.call_args_list[0].args[0]
    second_call_steps = mock_execute.call_args_list[1].args[0]
    assert first_call_steps[1]["selector"] == "#checkout-button"
    # second call received the HEALED selector, not the original
    assert second_call_steps[1]["selector"] == '[data-testid="checkout-submit"]'
    assert second_call_steps[1]["id"] == "gen-click-1"  # same step, only selector changed
    assert second_call_steps[0] == first_call_steps[0]  # untouched navigate step identical


def test_healing_never_reported_when_original_execution_passes(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_DUAL_EVIDENCE)

    with patch(
        "app.api.routes.test_definitions.execute_steps", return_value=_passing_result()
    ) as mock_execute:
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    assert body["healing"]["status"] == "not_attempted"
    assert body["healing"]["applied"] is False
    mock_execute.assert_called_once()


# --- 9. failed second execution -> healing_failed, not healed ---


def test_healing_applied_but_second_execution_fails_reports_healing_failed(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_DUAL_EVIDENCE)

    original_failure = _failing_result("gen-click-1", _SELECTOR_NOT_FOUND_ERROR)
    healed_failure = _failing_result("gen-click-1", "page.click: Timeout 5000ms exceeded.")

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[original_failure, healed_failure],
    ) as mock_execute:
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    healing = body["healing"]
    assert healing["status"] == "healing_failed"
    assert healing["applied"] is True
    assert healing["healed_execution"]["status"] == "failed"
    assert mock_execute.call_count == 2


# --- 10. APPLICATION_BUG -> no healing attempt ---


def test_application_bug_never_triggers_a_healing_attempt(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_DUAL_EVIDENCE)

    server_error = _failing_result("gen-click-1", "Request failed with status code 503")

    with patch(
        "app.api.routes.test_definitions.execute_steps", return_value=server_error
    ) as mock_execute:
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    assert body["diagnosis"]["classification"] == "APPLICATION_BUG"
    assert body["healing"]["status"] == "not_eligible"
    assert body["healing"]["applied"] is False
    # exactly ONE execute_steps call -- no healing attempt was made at all
    mock_execute.assert_called_once()


# --- 11. eligible but no candidate -> no_candidate ---


def test_eligible_failure_with_only_one_known_identifier_reports_no_candidate(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_SINGLE_EVIDENCE)

    failure = _failing_result("gen-click-1", _SELECTOR_NOT_FOUND_ERROR)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=failure) as mock_execute:
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    assert body["diagnosis"]["classification"] == "UNCERTAIN"
    healing = body["healing"]
    assert healing["status"] == "no_candidate"
    assert healing["applied"] is False
    assert healing["proposed_selector"] is None  # never fabricated
    # exactly ONE execute_steps call -- no candidate, so no second attempt
    mock_execute.assert_called_once()


# --- 12. exactly one healing attempt maximum ---


def test_at_most_one_healing_attempt_is_ever_made(client):
    """
    Even in the successful-healing case, execute_steps is called at
    most twice total (original + one healing attempt) -- there is no
    loop, no re-diagnosis of the healed result, and no third attempt
    regardless of the healed execution's own outcome.
    """
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_DUAL_EVIDENCE)

    # Even the "healed" run is itself made to fail with what LOOKS like
    # another healable selector error -- if a loop existed, this would
    # trigger a third execute_steps() call. It must not.
    original_failure = _failing_result("gen-click-1", _SELECTOR_NOT_FOUND_ERROR)
    healed_also_fails_similarly = _failing_result("gen-click-1", _SELECTOR_NOT_FOUND_ERROR)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[original_failure, healed_also_fails_similarly],
    ) as mock_execute:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.json()["healing"]["status"] == "healing_failed"
    assert mock_execute.call_count == 2  # never 3


# --- original TestDefinition protection ---


def test_original_test_definition_is_never_modified_by_healing(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_DUAL_EVIDENCE)

    original_failure = _failing_result("gen-click-1", _SELECTOR_NOT_FOUND_ERROR)
    healed_success = _passing_result()

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[original_failure, healed_success],
    ):
        client.post(f"/tests/{test_id}/execute")

    # Re-fetch the TestDefinition after healing and confirm its stored
    # content is byte-for-byte unchanged from what was originally created.
    stored = client.get(f"/tests/{test_id}")
    assert stored.status_code == 200
    stored_click_step = stored.json()["content"][1]
    assert stored_click_step["selector"] == "#checkout-button"  # original, not healed
    assert stored_click_step["selectorKind"] == "id"


def test_original_and_healed_execution_results_remain_distinguishable(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, _STEPS_WITH_DUAL_EVIDENCE)

    original_failure = _failing_result("gen-click-1", _SELECTOR_NOT_FOUND_ERROR)
    healed_success = _passing_result()

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=[original_failure, healed_success],
    ):
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    # Top-level execution result is still the ORIGINAL (failed) run --
    # healing does not overwrite the top-level response with the
    # healed outcome.
    assert body["status"] == "failed"
    assert body["failedStepId"] == "gen-click-1"
    # The healed run's outcome is only ever visible nested under `healing`.
    assert body["healing"]["healed_execution"]["status"] == "passed"


# --- no fabricated selector/evidence ---


def test_healing_never_fabricates_a_selector_when_no_evidence_exists(client):
    # A step with NEITHER a stable id nor data-testid evidence field at
    # all -- the oldest possible legacy content shape.
    steps = [
        {"id": "gen-nav-1", "type": "navigate", "url": "https://shop.test/"},
        {"id": "gen-click-1", "type": "click", "selector": "#mystery-button", "selectorKind": "id"},
    ]
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id, steps)

    failure = _failing_result("gen-click-1", _SELECTOR_NOT_FOUND_ERROR)

    with patch("app.api.routes.test_definitions.execute_steps", return_value=failure):
        response = client.post(f"/tests/{test_id}/execute")

    healing = response.json()["healing"]
    assert healing["status"] == "no_candidate"
    assert healing["proposed_selector"] is None
    assert healing["proposed_selector_kind"] is None
