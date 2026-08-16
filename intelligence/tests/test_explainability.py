"""
Focused unit tests for the Explainability Foundation.

These tests intentionally construct FailureDiagnosisResult directly
(rather than driving the full Recorder -> Intelligence -> Execution
pipeline) since explainability's contract is with FailureDiagnosisResult
itself, not with how it was produced. One integration-style test at the
end confirms it also works against a diagnosis produced by the real
diagnose_execution_result() path.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from intelligence.diagnosis import (
    APPLICATION_BUG,
    BROKEN_TEST,
    ENVIRONMENT_OR_EXECUTION,
    UNCERTAIN,
    ExecutionResult,
    STATUS_PASSED,
    STATUS_FAILED,
    FailureDiagnosisResult,
)
from intelligence.diagnosis.failure_diagnosis import diagnose_execution_result
from intelligence.journey_understanding.recorder_adapter import RealRecordedEvent
from intelligence.pipeline import generate_test_from_real_recorder_events

from intelligence.explainability import (
    explain_diagnosis,
    ExplainedDiagnosis,
    CONFIDENCE_HIGH,
    CONFIDENCE_MODERATE,
    CONFIDENCE_LOW,
)
from intelligence.explainability.engine import _headline


# ---------------------------------------------------------------------------
# No-failure (passed execution) case
# ---------------------------------------------------------------------------

def test_no_failure_produces_passed_headline_and_no_classification():
    diagnosis = FailureDiagnosisResult(
        has_failure=False,
        classification=None,
        confidence=1.0,
        correlation_established=False,
        evidence=["Execution status was 'passed'; there is no failure to diagnose."],
        explanation="Execution completed successfully. No diagnosis is necessary.",
    )

    result = explain_diagnosis(diagnosis)

    assert isinstance(result, ExplainedDiagnosis)
    assert result.has_failure is False
    assert result.classification is None
    assert result.confidence == 1.0
    assert result.confidence_level == CONFIDENCE_HIGH
    assert result.headline == "Execution passed"
    assert result.explanation == diagnosis.explanation
    assert result.evidence == diagnosis.evidence


# ---------------------------------------------------------------------------
# Classification / confidence / evidence / explanation must pass through
# verbatim -- explainability must not alter or re-derive them.
# ---------------------------------------------------------------------------

def test_application_bug_passes_through_classification_and_confidence_verbatim():
    diagnosis = FailureDiagnosisResult(
        has_failure=True,
        classification=APPLICATION_BUG,
        confidence=0.7,
        correlation_established=True,
        failed_step_id="gen-step-2",
        failed_step_index=1,
        error="Request failed with status code 503",
        generated_step_id="gen-step-2",
        source_step_id="step-rec-evt-2",
        source_event_id="rec-evt-2",
        evidence=[
            "Execution failed at step 'gen-step-2' (type: click), correlated via failedStepId.",
            "The error text contains a pattern consistent with an HTTP server error (5xx).",
        ],
        explanation="The reported error text matches a server-error (5xx) pattern.",
    )

    result = explain_diagnosis(diagnosis)

    assert result.classification == APPLICATION_BUG
    assert result.confidence == 0.7
    assert result.confidence_level == CONFIDENCE_HIGH
    assert result.headline == "Likely an application bug"
    assert result.explanation == diagnosis.explanation
    assert result.evidence == diagnosis.evidence
    # Must be a copy, not the same list object, so callers can't mutate
    # the original diagnosis result through the explanation.
    assert result.evidence is not diagnosis.evidence


def test_environment_or_execution_moderate_confidence():
    diagnosis = FailureDiagnosisResult(
        has_failure=True,
        classification=ENVIRONMENT_OR_EXECUTION,
        confidence=0.55,
        correlation_established=True,
        evidence=["The error text matches timeout/network/connection-related keywords."],
        explanation="Classified as an environment/execution issue.",
    )

    result = explain_diagnosis(diagnosis)

    assert result.classification == ENVIRONMENT_OR_EXECUTION
    assert result.confidence == 0.55
    assert result.confidence_level == CONFIDENCE_MODERATE
    assert result.headline == "Likely an environment or execution issue"


def test_uncertain_low_confidence():
    diagnosis = FailureDiagnosisResult(
        has_failure=True,
        classification=UNCERTAIN,
        confidence=0.15,
        correlation_established=True,
        evidence=["The error text did not match any known deterministic pattern."],
        explanation="Classifying as uncertain rather than guessing.",
    )

    result = explain_diagnosis(diagnosis)

    assert result.classification == UNCERTAIN
    assert result.confidence == 0.15
    assert result.confidence_level == CONFIDENCE_LOW
    assert result.headline == "Cause is uncertain"


def test_broken_test_classification_maps_to_its_own_headline():
    # BROKEN_TEST is only ever produced by the Task 3 local-fixture
    # prototype today (the real pipeline forces selector-looking
    # failures to UNCERTAIN -- see failure_diagnosis.py). Explainability
    # must still handle it correctly since it's a valid category on
    # FailureDiagnosisResult's own type.
    diagnosis = FailureDiagnosisResult(
        has_failure=True,
        classification=BROKEN_TEST,
        confidence=0.75,
        correlation_established=True,
        evidence=["An element with matching tag, role, and overlapping text was found."],
        explanation="The recorded selector is outdated but an equivalent element still exists.",
    )

    result = explain_diagnosis(diagnosis)

    assert result.classification == BROKEN_TEST
    assert result.confidence_level == CONFIDENCE_HIGH
    assert result.headline == "Likely an outdated/broken test"


# ---------------------------------------------------------------------------
# confidence_level thresholding -- boundary values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "confidence,expected_level",
    [
        (1.0, CONFIDENCE_HIGH),
        (0.9, CONFIDENCE_HIGH),
        (0.7, CONFIDENCE_HIGH),   # lower boundary of HIGH, inclusive
        (0.69, CONFIDENCE_MODERATE),
        (0.6, CONFIDENCE_MODERATE),
        (0.4, CONFIDENCE_MODERATE),  # lower boundary of MODERATE, inclusive
        (0.39, CONFIDENCE_LOW),
        (0.1, CONFIDENCE_LOW),
        (0.0, CONFIDENCE_LOW),
    ],
)
def test_confidence_level_thresholds(confidence, expected_level):
    diagnosis = FailureDiagnosisResult(
        has_failure=True,
        classification=UNCERTAIN,
        confidence=confidence,
        correlation_established=False,
        evidence=[],
        explanation="",
    )

    result = explain_diagnosis(diagnosis)

    assert result.confidence_level == expected_level


# ---------------------------------------------------------------------------
# Determinism: same input always produces the same output.
# ---------------------------------------------------------------------------

def test_explain_diagnosis_is_deterministic():
    diagnosis = FailureDiagnosisResult(
        has_failure=True,
        classification=APPLICATION_BUG,
        confidence=0.7,
        correlation_established=True,
        evidence=["Reported error: Request failed with status code 500"],
        explanation="Matches a server-error pattern.",
    )

    first = explain_diagnosis(diagnosis)
    second = explain_diagnosis(diagnosis)

    assert first == second


# ---------------------------------------------------------------------------
# Rejects an unrecognized classification rather than guessing wording.
# ---------------------------------------------------------------------------

def test_unrecognized_classification_raises_rather_than_guessing():
    # FailureDiagnosisResult already validates classification in its own
    # __post_init__, so an invalid one can never actually reach
    # explain_diagnosis() through normal construction -- that upstream
    # guard is diagnosis's job, not explainability's to duplicate. This
    # test instead exercises explainability's own internal safety net
    # directly (_headline), confirming that IF an unrecognized
    # classification ever did reach it, it would fail loudly rather
    # than invent headline wording for a category it doesn't know.
    with pytest.raises(ValueError):
        _headline(has_failure=True, classification="SOME_FUTURE_CATEGORY")


# ---------------------------------------------------------------------------
# Integration: explainability against a diagnosis produced by the real
# diagnose_execution_result() path (not a hand-built fixture).
# ---------------------------------------------------------------------------

def _three_step_generated_test():
    events = [
        RealRecordedEvent(
            id="rec-evt-1", type="page_load", timestamp=1000.0, pageUrl="https://shop.test/"
        ),
        RealRecordedEvent(
            id="rec-evt-2",
            type="click",
            timestamp=1001.0,
            pageUrl="https://shop.test/",
            targetTag="a",
            elementId="data-testid:nav-products",
            elementText="Products",
        ),
        RealRecordedEvent(
            id="rec-evt-3",
            type="input_change",
            timestamp=1002.0,
            pageUrl="https://shop.test/search",
            targetTag="input",
            elementId="search-box",
            value="running shoes",
        ),
    ]
    return generate_test_from_real_recorder_events("j1", events)


def test_explain_diagnosis_against_real_pipeline_output():
    generated = _three_step_generated_test()
    failed_step_id = generated.steps[1].step_id  # the click step

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId=failed_step_id,
        error="Request failed with status code 503",
        executedStepCount=2,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)
    result = explain_diagnosis(diagnosis)

    # Explainability must not alter what diagnosis decided.
    assert result.classification == diagnosis.classification
    assert result.confidence == diagnosis.confidence
    assert result.evidence == diagnosis.evidence
    assert result.explanation == diagnosis.explanation
    assert result.headline == "Likely an application bug"


def test_explain_diagnosis_against_real_pipeline_passed_run():
    generated = _three_step_generated_test()

    execution_result = ExecutionResult(
        status=STATUS_PASSED,
        failedStepIndex=None,
        failedStepId=None,
        error=None,
        executedStepCount=3,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)
    result = explain_diagnosis(diagnosis)

    assert result.has_failure is False
    assert result.classification is None
    assert result.headline == "Execution passed"
