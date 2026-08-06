"""
Focused tests for the Task 3 deterministic diagnosis prototype.

These tests use only LOCAL prototype fixtures — they do not depend on,
and are not validating, any shared contract.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from intelligence.diagnosis import (
    diagnose,
    LocalRecordedJourney,
    LocalJourneyStep,
    LocalExecutionFailure,
    LocalElementInfo,
    LocalDiagnosisResult,
)
from intelligence.diagnosis.engine import (
    APPLICATION_BUG,
    BROKEN_TEST,
    ENVIRONMENT_OR_EXECUTION,
    UNCERTAIN,
)


def _make_journey(steps=None, current_dom_elements=None):
    return LocalRecordedJourney(
        journey_id="journey-1",
        steps=steps or [],
        current_dom_elements=current_dom_elements or [],
    )


def test_http_500_classified_as_application_bug():
    journey = _make_journey(
        steps=[LocalJourneyStep(step_id="step-checkout", action_type="click")]
    )
    failure = LocalExecutionFailure(
        run_id="run-1",
        failed_step_id="step-checkout",
        error_type="HTTP_ERROR",
        http_status=500,
        error_message="Internal Server Error",
    )

    result = diagnose(journey, failure)

    assert result.category == APPLICATION_BUG
    assert result.confidence >= 0.8
    assert result.healing_should_be_considered is False
    assert any("500" in e for e in result.evidence)


def test_selector_not_found_with_equivalent_element_is_broken_test():
    login_button = LocalElementInfo(
        tag="button", role="button", text="Login", selector="#login-btn"
    )
    journey = _make_journey(
        steps=[
            LocalJourneyStep(step_id="step-login", action_type="click", element=login_button)
        ],
        current_dom_elements=[
            LocalElementInfo(
                tag="button", role="button", text="Sign In / Login", selector="#signin-button"
            )
        ],
    )
    failure = LocalExecutionFailure(
        run_id="run-2",
        failed_step_id="step-login",
        error_type="SELECTOR_NOT_FOUND",
        attempted_selector="#login-btn",
    )

    result = diagnose(journey, failure)

    assert result.category == BROKEN_TEST
    assert 0.5 <= result.confidence < 1.0
    assert result.healing_should_be_considered is True
    assert any("#signin-button" in e for e in result.evidence)


def test_selector_not_found_with_no_equivalent_element_is_uncertain():
    missing_button = LocalElementInfo(
        tag="button", role="button", text="Checkout", selector="#checkout-btn"
    )
    journey = _make_journey(
        steps=[
            LocalJourneyStep(step_id="step-checkout", action_type="click", element=missing_button)
        ],
        current_dom_elements=[
            LocalElementInfo(tag="a", role="link", text="Home", selector="#home-link")
        ],
    )
    failure = LocalExecutionFailure(
        run_id="run-3",
        failed_step_id="step-checkout",
        error_type="SELECTOR_NOT_FOUND",
        attempted_selector="#checkout-btn",
    )

    result = diagnose(journey, failure)

    assert result.category == UNCERTAIN
    assert result.confidence <= 0.4
    assert result.healing_should_be_considered is False


def test_timeout_classified_as_environment_or_execution():
    journey = _make_journey(
        steps=[LocalJourneyStep(step_id="step-load", action_type="navigate")]
    )
    failure = LocalExecutionFailure(
        run_id="run-4",
        failed_step_id="step-load",
        error_type="TIMEOUT",
        error_message="Navigation timeout of 30000ms exceeded",
    )

    result = diagnose(journey, failure)

    assert result.category == ENVIRONMENT_OR_EXECUTION
    assert 0.4 <= result.confidence < 0.8
    assert result.healing_should_be_considered is False


def test_unknown_error_type_falls_back_to_uncertain():
    journey = _make_journey(
        steps=[LocalJourneyStep(step_id="step-x", action_type="click")]
    )
    failure = LocalExecutionFailure(
        run_id="run-5",
        failed_step_id="step-x",
        error_type="SOMETHING_UNEXPECTED",
    )

    result = diagnose(journey, failure)

    assert result.category == UNCERTAIN
    assert result.confidence < 0.3


def test_diagnosis_result_rejects_invalid_category():
    try:
        LocalDiagnosisResult(
            run_id="run-x", category="NOT_A_REAL_CATEGORY", confidence=0.5
        )
        raised = False
    except ValueError:
        raised = True
    assert raised, "Expected ValueError for invalid category"


def test_diagnosis_result_rejects_out_of_range_confidence():
    try:
        LocalDiagnosisResult(run_id="run-x", category=UNCERTAIN, confidence=1.5)
        raised = False
    except ValueError:
        raised = True
    assert raised, "Expected ValueError for out-of-range confidence"


def test_evidence_is_never_fabricated_beyond_input_fields():
    """
    Sanity check: every evidence string for the HTTP_ERROR path must be
    traceable to fields actually present on the input failure/journey,
    not invented content.
    """
    journey = _make_journey(
        steps=[LocalJourneyStep(step_id="step-pay", action_type="click")]
    )
    failure = LocalExecutionFailure(
        run_id="run-6",
        failed_step_id="step-pay",
        error_type="HTTP_ERROR",
        http_status=503,
        error_message="Service Unavailable",
    )

    result = diagnose(journey, failure)

    combined_evidence = " ".join(result.evidence)
    assert failure.failed_step_id in combined_evidence
    assert str(failure.http_status) in combined_evidence
    assert failure.error_message in combined_evidence


if __name__ == "__main__":
    # Plain-Python runner so this suite works even without pytest installed.
    # If pytest is available in the actual dev environment, prefer:
    #   pytest intelligence/tests/test_diagnosis.py -v
    test_functions = [
        (name, obj)
        for name, obj in list(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    passed, failed = 0, 0
    for name, fn in test_functions:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {name} -> {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {name} -> {e!r}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
