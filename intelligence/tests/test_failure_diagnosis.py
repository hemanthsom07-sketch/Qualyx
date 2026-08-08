"""
Tests for Task 10: the deterministic failure-diagnosis foundation that
consumes Claude 2's real ExecutionResult contract together with a
LocalGeneratedTest produced by the real Recorder pipeline.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from intelligence.journey_understanding.recorder_adapter import RealRecordedEvent
from intelligence.pipeline import (
    generate_test_from_real_recorder_events,
    prepare_integration_ready_test_from_real_recorder_events,
    diagnose_execution,
)
from intelligence.diagnosis import (
    ExecutionResult,
    STATUS_PASSED,
    STATUS_FAILED,
    APPLICATION_BUG,
    BROKEN_TEST,
    ENVIRONMENT_OR_EXECUTION,
    UNCERTAIN,
)
from intelligence.diagnosis.failure_diagnosis import diagnose_execution_result


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


def test_successful_execution_produces_no_failure_diagnosis():
    generated = _three_step_generated_test()
    execution_result = ExecutionResult(
        status=STATUS_PASSED,
        failedStepIndex=None,
        failedStepId=None,
        error=None,
        executedStepCount=3,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.has_failure is False
    assert diagnosis.classification is None
    assert diagnosis.correlation_established is False


def test_application_bug_classification_from_http_5xx_pattern():
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

    assert diagnosis.has_failure is True
    assert diagnosis.classification == APPLICATION_BUG
    assert diagnosis.correlation_established is True
    assert 0.5 <= diagnosis.confidence < 0.9
    assert diagnosis.generated_step_id == failed_step_id


def test_environment_or_execution_classification_from_timeout_keyword():
    generated = _three_step_generated_test()
    failed_step_id = generated.steps[0].step_id  # navigate step

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=0,
        failedStepId=failed_step_id,
        error="Navigation timeout of 30000ms exceeded",
        executedStepCount=0,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.classification == ENVIRONMENT_OR_EXECUTION
    assert diagnosis.correlation_established is True
    assert 0.4 <= diagnosis.confidence < 0.7


def test_selector_related_error_is_uncertain_not_broken_test_or_app_bug():
    generated = _three_step_generated_test()
    failed_step_id = generated.steps[1].step_id

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId=failed_step_id,
        error="Locator not found: [data-testid=\"nav-products\"]",
        executedStepCount=1,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    # A generic error string cannot reliably distinguish broken test
    # from a genuine application change -- must be UNCERTAIN, not
    # BROKEN_TEST or APPLICATION_BUG.
    assert diagnosis.classification == UNCERTAIN
    assert diagnosis.correlation_established is True
    assert diagnosis.confidence < 0.4


def test_unrecognized_error_text_falls_back_to_uncertain():
    generated = _three_step_generated_test()
    failed_step_id = generated.steps[2].step_id

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=2,
        failedStepId=failed_step_id,
        error="Something unexpected happened",
        executedStepCount=2,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.classification == UNCERTAIN
    assert diagnosis.correlation_established is True
    assert diagnosis.confidence < 0.3


def test_failed_step_id_correctly_maps_to_generated_step():
    generated = _three_step_generated_test()
    target_step = generated.steps[1]

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId=target_step.step_id,
        error="500 Internal Server Error",
        executedStepCount=1,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.generated_step_id == target_step.step_id


def test_source_event_id_provenance_survives_diagnosis():
    generated = _three_step_generated_test()
    target_step = generated.steps[1]
    assert target_step.source_event_id == "rec-evt-2"

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId=target_step.step_id,
        error="503 Service Unavailable",
        executedStepCount=1,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.source_event_id == "rec-evt-2"


def test_source_step_id_provenance_survives_diagnosis():
    generated = _three_step_generated_test()
    target_step = generated.steps[1]

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId=target_step.step_id,
        error="503 Service Unavailable",
        executedStepCount=1,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.source_step_id == target_step.source_step_id
    assert diagnosis.source_step_id == "step-rec-evt-2"


def test_missing_failed_step_id_does_not_fabricate_an_id():
    generated = _three_step_generated_test()

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId=None,
        error="500 Internal Server Error",
        executedStepCount=1,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.classification == UNCERTAIN
    assert diagnosis.correlation_established is False
    assert diagnosis.failed_step_id is None
    assert diagnosis.generated_step_id is None
    assert diagnosis.source_event_id is None
    assert diagnosis.source_step_id is None


def test_unknown_failed_step_id_produces_safe_uncertain_diagnosis():
    generated = _three_step_generated_test()

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId="gen-step-does-not-exist",
        error="500 Internal Server Error",
        executedStepCount=1,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.classification == UNCERTAIN
    assert diagnosis.correlation_established is False
    # The unknown id is still reported verbatim (not fabricated away),
    # but no generated step is claimed to match it.
    assert diagnosis.failed_step_id == "gen-step-does-not-exist"
    assert diagnosis.generated_step_id is None


def test_failed_step_index_alone_never_becomes_correlation_key():
    """
    Even with a valid-looking failedStepIndex, if failedStepId is
    missing/unmatched, the diagnosis must not silently use the index
    to look up generated_test.steps[index] as if it were correlation.
    """
    generated = _three_step_generated_test()
    # Index 1 legitimately refers to the click step in this generated
    # test, but failedStepId is deliberately absent -- correlation
    # must still fail rather than falling back to index lookup.
    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId=None,
        error="500 Internal Server Error",
        executedStepCount=1,
    )

    diagnosis = diagnose_execution_result(generated, execution_result)

    assert diagnosis.correlation_established is False
    assert diagnosis.generated_step_id is None
    # The index is preserved as supplementary evidence only.
    assert diagnosis.failed_step_index == 1
    assert any("failedStepIndex" in e for e in diagnosis.evidence)


def test_diagnosis_is_deterministic_across_repeated_calls():
    generated = _three_step_generated_test()
    target_step = generated.steps[1]
    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=1,
        failedStepId=target_step.step_id,
        error="502 Bad Gateway",
        executedStepCount=1,
    )

    diagnosis_a = diagnose_execution_result(generated, execution_result)
    diagnosis_b = diagnose_execution_result(generated, execution_result)

    assert diagnosis_a.classification == diagnosis_b.classification
    assert diagnosis_a.confidence == diagnosis_b.confidence
    assert diagnosis_a.generated_step_id == diagnosis_b.generated_step_id
    assert diagnosis_a.evidence == diagnosis_b.evidence


def test_pipeline_diagnose_execution_accepts_integration_ready_result():
    events = [
        RealRecordedEvent(
            id="rec-evt-1", type="page_load", timestamp=1000.0, pageUrl="https://shop.test/"
        ),
    ]
    bundled = prepare_integration_ready_test_from_real_recorder_events("j1", events)
    target_step = bundled.generated_test.steps[0]

    execution_result = ExecutionResult(
        status=STATUS_FAILED,
        failedStepIndex=0,
        failedStepId=target_step.step_id,
        error="503 Service Unavailable",
        executedStepCount=0,
    )

    diagnosis = diagnose_execution(bundled, execution_result)

    assert diagnosis.has_failure is True
    assert diagnosis.classification == APPLICATION_BUG
    assert diagnosis.generated_step_id == target_step.step_id


def test_pipeline_diagnose_execution_accepts_plain_generated_test():
    generated = _three_step_generated_test()
    execution_result = ExecutionResult(status=STATUS_PASSED, executedStepCount=3)

    diagnosis = diagnose_execution(generated, execution_result)

    assert diagnosis.has_failure is False


if __name__ == "__main__":
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
