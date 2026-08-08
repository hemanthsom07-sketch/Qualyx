"""
Tests for Task 9: preparing a single, bundled, execution-ready +
provenance-rich test representation from real Recorder events, without
recomputing the pipeline twice or losing any existing guarantee.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from intelligence.journey_understanding.recorder_adapter import RealRecordedEvent
from intelligence.pipeline import (
    prepare_integration_ready_test_from_real_recorder_events,
    generate_test_from_real_recorder_events,
    generate_execution_payload_from_real_recorder_events,
)
from intelligence.test_generation import GEN_STEP_NAVIGATE, GEN_STEP_CLICK, GEN_STEP_FILL


def _realistic_mixed_events():
    """
    A realistic mixed journey: navigate, an unsupported event, a click
    with a data-testid selector, a normal fill, a redacted fill, and a
    click with no stable selector at all.
    """
    return [
        RealRecordedEvent(
            id="rec-evt-1", type="page_load", timestamp=1000.0, pageUrl="https://shop.test/login"
        ),
        RealRecordedEvent(
            id="rec-evt-2", type="mousemove", timestamp=1000.2, pageUrl="https://shop.test/login"
        ),  # unsupported
        RealRecordedEvent(
            id="rec-evt-3",
            type="input_change",
            timestamp=1000.5,
            pageUrl="https://shop.test/login",
            targetTag="input",
            elementId="data-testid:username-input",
            value="jane@example.com",
        ),
        RealRecordedEvent(
            id="rec-evt-4",
            type="input_change",
            timestamp=1000.7,
            pageUrl="https://shop.test/login",
            targetTag="input",
            elementId="data-testid:password-input",
            value=None,
            redacted=True,
        ),
        RealRecordedEvent(
            id="rec-evt-5",
            type="click",
            timestamp=1001.0,
            pageUrl="https://shop.test/login",
            targetTag="div",
            elementId=None,  # no stable selector
            elementText="Forgot password?",
        ),
        RealRecordedEvent(
            id="rec-evt-6",
            type="click",
            timestamp=1001.2,
            pageUrl="https://shop.test/login",
            targetTag="button",
            elementId="data-testid:signin-button",
            elementText="Sign In",
        ),
    ]


def test_bundled_result_execution_payload_matches_standalone_payload_entry_point():
    events = _realistic_mixed_events()

    bundled = prepare_integration_ready_test_from_real_recorder_events("journey-1", events)
    standalone_payload = generate_execution_payload_from_real_recorder_events("journey-1", events)

    assert bundled.execution_payload == standalone_payload


def test_bundled_result_generated_test_matches_standalone_generated_test_entry_point():
    events = _realistic_mixed_events()

    bundled = prepare_integration_ready_test_from_real_recorder_events("journey-1", events)
    standalone_generated = generate_test_from_real_recorder_events("journey-1", events)

    assert [s.step_id for s in bundled.generated_test.steps] == [
        s.step_id for s in standalone_generated.steps
    ]
    assert [u.reason for u in bundled.generated_test.ungeneratable_steps] == [
        u.reason for u in standalone_generated.ungeneratable_steps
    ]


def test_bundled_result_preserves_ordering_across_supported_and_unsupported_events():
    bundled = prepare_integration_ready_test_from_real_recorder_events(
        "journey-1", _realistic_mixed_events()
    )

    # rec-evt-2 (mousemove) is skipped; rec-evt-4 (redacted) and
    # rec-evt-5 (no stable selector) are ungeneratable but still
    # accounted for. Generated steps keep their relative order.
    assert [s.kind for s in bundled.generated_test.steps] == [
        GEN_STEP_NAVIGATE,
        GEN_STEP_FILL,
        GEN_STEP_CLICK,
    ]
    assert [s.step_id for s in bundled.generated_test.steps] == [
        "gen-step-rec-evt-1",
        "gen-step-rec-evt-3",
        "gen-step-rec-evt-6",
    ]
    assert [s["id"] for s in bundled.execution_payload["steps"]] == [
        "gen-step-rec-evt-1",
        "gen-step-rec-evt-3",
        "gen-step-rec-evt-6",
    ]


def test_bundled_result_reports_ungeneratable_steps_with_reasons_not_dropped_silently():
    bundled = prepare_integration_ready_test_from_real_recorder_events(
        "journey-1", _realistic_mixed_events()
    )

    ungen = bundled.generated_test.ungeneratable_steps
    assert len(ungen) == 2  # redacted password + no-stable-selector click

    reasons = " | ".join(u.reason for u in ungen)
    assert "redacted" in reasons.lower()
    assert "stable selector" in reasons.lower()
    # No invented placeholder value anywhere in the reasons.
    assert "[REDACTED]" not in reasons


def test_bundled_result_never_fabricates_selectors_urls_or_values():
    bundled = prepare_integration_ready_test_from_real_recorder_events(
        "journey-1", _realistic_mixed_events()
    )

    for step in bundled.execution_payload["steps"]:
        if step["type"] == GEN_STEP_CLICK or step["type"] == GEN_STEP_FILL:
            assert "selector" in step and step["selector"]
            # Only the two allowed stable-selector forms appear.
            assert step["selector"].startswith("[data-testid=") or step["selector"].startswith("#")
        if step["type"] == GEN_STEP_NAVIGATE:
            assert step["url"] == "https://shop.test/login"

    # The redacted step's value never appears anywhere in the payload.
    payload_str = str(bundled.execution_payload)
    assert "REDACTED" not in payload_str.upper() or "redacted" not in payload_str


def test_bundled_result_is_deterministic_across_repeated_calls():
    events = _realistic_mixed_events()

    bundled_a = prepare_integration_ready_test_from_real_recorder_events("journey-1", events)
    bundled_b = prepare_integration_ready_test_from_real_recorder_events("journey-1", events)

    assert bundled_a.execution_payload == bundled_b.execution_payload
    assert [s.step_id for s in bundled_a.generated_test.steps] == [
        s.step_id for s in bundled_b.generated_test.steps
    ]


def test_bundled_result_execution_payload_ids_correlate_to_generated_test_provenance():
    """
    Confirms the full correlation chain a next-integration-stage caller
    would rely on: payload "id" -> matching LocalGeneratedStep ->
    source_event_id/source_step_id, all from a single generation pass.
    """
    bundled = prepare_integration_ready_test_from_real_recorder_events(
        "journey-1", _realistic_mixed_events()
    )

    payload_ids = [s["id"] for s in bundled.execution_payload["steps"]]
    generated_by_id = {s.step_id: s for s in bundled.generated_test.steps}

    for pid in payload_ids:
        assert pid in generated_by_id
        step = generated_by_id[pid]
        assert step.source_step_id.startswith("step-")
        assert step.source_event_id is not None


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
