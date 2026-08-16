"""
Tests for the Backend -> Intelligence diagnosis bridge, wired into
POST /tests/{test_id}/execute.

Rewritten for the Milestone 2A contract. The route no longer exposes a
two-arg `diagnose(test_definition, execution_result)` boundary. It now
calls:

    diagnose_and_explain(test_definition_id: str, content: list[dict],
                          execution_result: ExecutionResultOut)
        -> tuple[FailureDiagnosisResult, ExplainedDiagnosis]

(see app/services/diagnosis_client.py), imported directly into
app.api.routes.test_definitions's namespace, and the route always
attaches BOTH resulting objects to the response as `diagnosis`
(DiagnosisOut, snake_case fields, mirroring FailureDiagnosisResult) and
`explanation` (ExplanationOut, mirroring ExplainedDiagnosis) --
app/schemas/diagnosis.py, not app/schemas/execution.py.

One behavioral consequence of the current wiring, different from the
previous contract these tests were written against: diagnose_and_explain
is now called UNCONDITIONALLY after every successful execute_steps()
call -- including a passing execution -- rather than being skipped on
success. Diagnosis itself decides internally that a passing run has no
failure to diagnose (has_failure=False, classification=None); the route
does not special-case "skip diagnosis on pass" anymore. Test 1 below is
updated to verify that outcome (a passing run correctly and only ever
produces a no-failure diagnosis, never a spuriously-failed one) rather
than asserting the bridge function itself goes uncalled, since it no
longer does.

As before, these tests mock the boundary function itself
(diagnose_and_explain) rather than letting the real Intelligence
diagnosis run, to verify the ROUTE's wiring in isolation: is the
boundary called with the right arguments, at the right time, and is its
result attached to the response unaltered. This mirrors the existing
pattern of mocking execute_steps() in test_execution.py, for the same
reason: the Python test suite must stay runnable without a live
Node/Playwright process and without requiring the real `intelligence`
package to be importable from wherever pytest happens to run. (Separate,
full-stack coverage -- the real diagnose_and_explain() actually calling
into Intelligence -- lives in test_execution_diagnosis.py.)
"""

from dataclasses import dataclass, field
from unittest.mock import patch

from app.schemas.execution import ExecutionResultOut

STEP_CONTENT_WITH_IDS = [
    {"id": "gen-step-nav-1", "type": "navigate", "url": "https://example.com"},
    {"id": "gen-step-click-2", "type": "click", "selector": "#submit"},
]


# ---------------------------------------------------------------------------
# Lightweight stand-ins for FailureDiagnosisResult / ExplainedDiagnosis.
#
# diagnose_and_explain() returns real Intelligence dataclasses, and the
# route converts them via DiagnosisOut.model_validate(...) /
# ExplanationOut.model_validate(...), both configured with
# from_attributes=True -- so any object exposing the right attributes
# validates identically to the real dataclasses. Using local fakes here
# (rather than importing intelligence.diagnosis/explainability directly)
# keeps this test file's own import graph independent of whether the
# `intelligence` package happens to be importable in the environment
# running this suite, consistent with this file's original design intent.
# ---------------------------------------------------------------------------


@dataclass
class _FakeDiagnosis:
    has_failure: bool
    classification: str | None = None
    confidence: float = 0.0
    correlation_established: bool = False
    failed_step_id: str | None = None
    failed_step_index: int | None = None
    error: str | None = None
    generated_step_id: str | None = None
    source_step_id: str | None = None
    source_event_id: str | None = None
    evidence: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class _FakeExplanation:
    has_failure: bool
    classification: str | None = None
    confidence: float = 0.0
    confidence_level: str = "LOW"
    headline: str = ""
    explanation: str = ""
    evidence: list[str] = field(default_factory=list)


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


def _no_failure_diagnosis_and_explanation() -> tuple[_FakeDiagnosis, _FakeExplanation]:
    diagnosis = _FakeDiagnosis(
        has_failure=False,
        classification=None,
        confidence=1.0,
        correlation_established=False,
        evidence=["Execution status was 'passed'; there is no failure to diagnose."],
        explanation="Execution completed successfully. No diagnosis is necessary.",
    )
    explanation = _FakeExplanation(
        has_failure=False,
        classification=None,
        confidence=1.0,
        confidence_level="HIGH",
        headline="Execution passed",
        explanation=diagnosis.explanation,
        evidence=diagnosis.evidence,
    )
    return diagnosis, explanation


def _correlated_diagnosis_and_explanation() -> tuple[_FakeDiagnosis, _FakeExplanation]:
    diagnosis = _FakeDiagnosis(
        has_failure=True,
        classification="ENVIRONMENT_OR_EXECUTION",
        confidence=0.55,
        correlation_established=True,
        failed_step_id="gen-step-click-2",
        failed_step_index=1,
        error="page.click: Timeout 5000ms exceeded.",
        generated_step_id="gen-step-click-2",
        source_step_id=None,
        source_event_id=None,
        evidence=[
            "Execution failed at step 'gen-step-click-2' (type: click), correlated via failedStepId."
        ],
        explanation="The failure text matches a timeout/network-type pattern.",
    )
    explanation = _FakeExplanation(
        has_failure=True,
        classification="ENVIRONMENT_OR_EXECUTION",
        confidence=0.55,
        confidence_level="MODERATE",
        headline="Likely an environment or execution issue",
        explanation=diagnosis.explanation,
        evidence=diagnosis.evidence,
    )
    return diagnosis, explanation


def _uncertain_uncorrelated_diagnosis_and_explanation(
    failed_step_id=None,
) -> tuple[_FakeDiagnosis, _FakeExplanation]:
    diagnosis = _FakeDiagnosis(
        has_failure=True,
        classification="UNCERTAIN",
        confidence=0.1,
        correlation_established=False,
        failed_step_id=failed_step_id,
        failed_step_index=1,
        error="some failure",
        generated_step_id=None,
        source_step_id=None,
        source_event_id=None,
        evidence=["Execution status was 'failed', but the failed step could not be correlated."],
        explanation="No matching stable step id was available.",
    )
    explanation = _FakeExplanation(
        has_failure=True,
        classification="UNCERTAIN",
        confidence=0.1,
        confidence_level="LOW",
        headline="Cause is uncertain",
        explanation=diagnosis.explanation,
        evidence=diagnosis.evidence,
    )
    return diagnosis, explanation


# --- 1. a passing execution correctly produces a no-failure diagnosis ---
#
# Under the current wiring, diagnose_and_explain() is called
# unconditionally after every successful execute_steps() call -- the
# route no longer skips it on a pass. What must be preserved is the
# outcome: a passing run's diagnosis/explanation must reflect
# has_failure=False / classification=None, never a fabricated failure.

def test_passing_execution_produces_no_failure_diagnosis(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps", return_value=_passing_result()
    ), patch(
        "app.api.routes.test_definitions.diagnose_and_explain",
        return_value=_no_failure_diagnosis_and_explanation(),
    ) as mock_diagnose_and_explain:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "passed"
    assert body["diagnosis"]["has_failure"] is False
    assert body["diagnosis"]["classification"] is None
    assert body["explanation"]["has_failure"] is False
    assert body["explanation"]["headline"] == "Execution passed"
    mock_diagnose_and_explain.assert_called_once()


# --- 2. a correlated execution failure reaches the diagnosis bridge and
#        is attached to the response ---

def test_correlated_failure_invokes_diagnosis_and_attaches_result(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)
    failing_result = _failing_result(failed_step_id="gen-step-click-2")

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=failing_result,
    ), patch(
        "app.api.routes.test_definitions.diagnose_and_explain",
        return_value=_correlated_diagnosis_and_explanation(),
    ) as mock_diagnose_and_explain:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"

    mock_diagnose_and_explain.assert_called_once()
    # diagnose_and_explain(test_definition_id: str, content: list[dict],
    # execution_result: ExecutionResultOut) -- verify the route passes
    # exactly the stored id/content and the real ExecutionResultOut
    # object through, unmodified.
    called_args = mock_diagnose_and_explain.call_args.args
    assert called_args[0] == test_id
    assert called_args[1] == STEP_CONTENT_WITH_IDS
    assert called_args[2] is failing_result

    diagnosis = body["diagnosis"]
    assert diagnosis["correlation_established"] is True
    assert diagnosis["generated_step_id"] == "gen-step-click-2"
    assert diagnosis["classification"] == "ENVIRONMENT_OR_EXECUTION"

    explanation = body["explanation"]
    assert explanation["classification"] == "ENVIRONMENT_OR_EXECUTION"
    assert explanation["headline"] == "Likely an environment or execution issue"


# --- 3 & 4. uncorrelated failures (null and unknown failedStepId) preserve
#            the UNCERTAIN contract, with no fabricated correlation ---

def test_failure_with_null_failed_step_id_preserves_uncertain_contract(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(failed_step_id=None),
    ), patch(
        "app.api.routes.test_definitions.diagnose_and_explain",
        return_value=_uncertain_uncorrelated_diagnosis_and_explanation(failed_step_id=None),
    ) as mock_diagnose_and_explain:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    diagnosis = response.json()["diagnosis"]
    assert diagnosis["correlation_established"] is False
    assert diagnosis["classification"] == "UNCERTAIN"
    assert diagnosis["failed_step_id"] is None
    assert diagnosis["generated_step_id"] is None
    assert response.json()["explanation"]["headline"] == "Cause is uncertain"
    mock_diagnose_and_explain.assert_called_once()


def test_failure_with_unknown_failed_step_id_preserves_uncertain_contract(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(failed_step_id="does-not-exist-in-generated-test"),
    ), patch(
        "app.api.routes.test_definitions.diagnose_and_explain",
        return_value=_uncertain_uncorrelated_diagnosis_and_explanation(
            failed_step_id="does-not-exist-in-generated-test"
        ),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 200
    diagnosis = response.json()["diagnosis"]
    assert diagnosis["correlation_established"] is False
    assert diagnosis["classification"] == "UNCERTAIN"
    # failedStepId is passed through verbatim (supplementary/informational),
    # but never treated as a successful correlation.
    assert diagnosis["failed_step_id"] == "does-not-exist-in-generated-test"
    assert diagnosis["generated_step_id"] is None


# --- 5. nested evidence.errorCategory remains nested, never top-level,
#        and coexists alongside the new diagnosis/explanation fields ---

def test_evidence_error_category_remains_nested_alongside_diagnosis(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(error_category="network"),
    ), patch(
        "app.api.routes.test_definitions.diagnose_and_explain",
        return_value=_correlated_diagnosis_and_explanation(),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    body = response.json()
    assert "errorCategory" not in body  # never top-level
    assert body["evidence"]["errorCategory"] == "network"  # only nested
    # ...and the additive diagnosis/explanation fields are still present
    # alongside it, unaffected.
    assert body["diagnosis"]["classification"] == "ENVIRONMENT_OR_EXECUTION"
    assert body["explanation"]["headline"] == "Likely an environment or execution issue"


# --- 6. source_step_id/source_event_id are never fabricated ---

def test_diagnosis_never_fabricates_provenance(client):
    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        return_value=_failing_result(),
    ), patch(
        "app.api.routes.test_definitions.diagnose_and_explain",
        return_value=_correlated_diagnosis_and_explanation(),
    ):
        response = client.post(f"/tests/{test_id}/execute")

    diagnosis = response.json()["diagnosis"]
    # Correlation succeeded (generated_step_id is set), but provenance
    # fields specifically remain null -- the route/schema must not invent
    # a value for them even when the rest of the diagnosis is confident.
    assert diagnosis["generated_step_id"] == "gen-step-click-2"
    assert diagnosis["source_step_id"] is None
    assert diagnosis["source_event_id"] is None


# --- 7. existing execution behavior remains intact ---

def test_execute_404_path_unaffected_by_diagnosis_bridge(client):
    response = client.post("/tests/does-not-exist/execute")
    assert response.status_code == 404


def test_execute_engine_error_path_unaffected_by_diagnosis_bridge(client):
    from app.services.execution_client import ExecutionEngineError

    project_id = _create_project(client)
    test_id = _create_test_definition(client, project_id)

    with patch(
        "app.api.routes.test_definitions.execute_steps",
        side_effect=ExecutionEngineError("boom"),
    ), patch(
        "app.api.routes.test_definitions.diagnose_and_explain"
    ) as mock_diagnose_and_explain:
        response = client.post(f"/tests/{test_id}/execute")

    assert response.status_code == 502
    # execute_steps raised before the diagnosis bridge is ever reached --
    # this remains genuinely true under the current wiring (the bridge
    # call sits after the try/except block), unlike test 1 above.
    mock_diagnose_and_explain.assert_not_called()
