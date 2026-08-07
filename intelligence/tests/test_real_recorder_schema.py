"""
Tests for the Task 5 correction: consuming the REAL Recorder
RecordedEvent schema (recorder/src/lib/eventCapture.ts) directly,
via journey_understanding.recorder_adapter and
pipeline.generate_test_from_real_recorder_events.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from intelligence.journey_understanding.recorder_adapter import (
    RealRecordedEvent,
    adapt_real_event,
)
from intelligence.pipeline import generate_test_from_real_recorder_events
from intelligence.test_generation import GEN_STEP_NAVIGATE, GEN_STEP_CLICK, GEN_STEP_FILL


def test_page_load_event_adapts_and_generates_navigate_step():
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="page_load",
            timestamp=1000.0,
            pageUrl="https://shop.test/",
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-1", events)

    assert len(generated.steps) == 1
    assert generated.steps[0].kind == GEN_STEP_NAVIGATE
    assert generated.steps[0].url == "https://shop.test/"
    assert generated.ungeneratable_steps == []


def test_click_event_with_real_html_id_produces_hash_selector():
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="click",
            timestamp=1001.0,
            pageUrl="https://shop.test/",
            targetTag="button",
            elementId="my-id",
            elementText="Continue",
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-2", events)

    assert generated.steps[0].kind == GEN_STEP_CLICK
    assert generated.steps[0].selector == "#my-id"
    assert generated.steps[0].selector_kind == "id"


def test_click_event_with_data_testid_encoding_produces_data_testid_selector():
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="click",
            timestamp=1002.0,
            pageUrl="https://shop.test/",
            targetTag="button",
            elementId="data-testid:my-test-id",
            elementText="Add to cart",
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-3", events)

    assert generated.steps[0].kind == GEN_STEP_CLICK
    assert generated.steps[0].selector == '[data-testid="my-test-id"]'
    assert generated.steps[0].selector_kind == "data-testid"


def test_input_change_with_normal_value_produces_fill_step():
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="input_change",
            timestamp=1003.0,
            pageUrl="https://shop.test/",
            targetTag="input",
            elementId="search-box",
            value="running shoes",
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-4", events)

    assert generated.steps[0].kind == GEN_STEP_FILL
    assert generated.steps[0].selector == "#search-box"
    assert generated.steps[0].value == "running shoes"


def test_sensitive_input_with_redacted_true_and_no_value_is_never_fabricated():
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="input_change",
            timestamp=1004.0,
            pageUrl="https://shop.test/login",
            targetTag="input",
            elementId="password-input",
            value=None,
            redacted=True,
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-5", events)

    # Must not silently generate a fill step with an invented value.
    assert generated.steps == []
    assert len(generated.ungeneratable_steps) == 1
    reason = generated.ungeneratable_steps[0].reason
    assert "redacted" in reason.lower()
    # Ensure no placeholder value like "[REDACTED]" was fabricated anywhere.
    assert "[REDACTED]" not in reason


def test_missing_stable_selector_is_never_guessed():
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="click",
            timestamp=1005.0,
            pageUrl="https://shop.test/",
            targetTag="div",
            elementId=None,
            elementText="Promo banner",
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-6", events)

    assert generated.steps == []
    assert len(generated.ungeneratable_steps) == 1
    assert "stable selector" in generated.ungeneratable_steps[0].reason


def test_full_realistic_sequence_preserves_ordering():
    events = [
        RealRecordedEvent(
            id="evt-1", type="page_load", timestamp=1000.0, pageUrl="https://shop.test/login"
        ),
        RealRecordedEvent(
            id="evt-2",
            type="input_change",
            timestamp=1001.0,
            pageUrl="https://shop.test/login",
            targetTag="input",
            elementId="username",
            value="jane@example.com",
        ),
        RealRecordedEvent(
            id="evt-3",
            type="input_change",
            timestamp=1002.0,
            pageUrl="https://shop.test/login",
            targetTag="input",
            elementId="password",
            value=None,
            redacted=True,
        ),
        RealRecordedEvent(
            id="evt-4",
            type="click",
            timestamp=1003.0,
            pageUrl="https://shop.test/login",
            targetTag="button",
            elementId="data-testid:signin-button",
            elementText="Sign In",
        ),
    ]

    generated = generate_test_from_real_recorder_events("journey-7", events)

    # 3 generatable steps (navigate, username fill, signin click) in order;
    # the redacted password step is reported separately, not silently dropped.
    assert [s.kind for s in generated.steps] == [
        GEN_STEP_NAVIGATE,
        GEN_STEP_FILL,
        GEN_STEP_CLICK,
    ]
    assert [s.source_step_id for s in generated.steps] == [
        "step-evt-1",
        "step-evt-2",
        "step-evt-4",
    ]
    assert len(generated.ungeneratable_steps) == 1
    assert generated.ungeneratable_steps[0].source_step_id == "step-evt-3"
    assert generated.steps[2].selector == '[data-testid="signin-button"]'


def test_adapter_treats_missing_redacted_flag_as_not_redacted():
    """The real contract's `redacted?: boolean` is optional; absence must
    not be treated as true."""
    event = RealRecordedEvent(
        id="evt-1",
        type="input_change",
        timestamp=1000.0,
        pageUrl="https://shop.test/",
        targetTag="input",
        elementId="promo-code",
        value="SAVE10",
        # redacted intentionally omitted (defaults to None in the dataclass)
    )

    adapted = adapt_real_event(event)

    assert adapted.redacted is False
    assert adapted.input_value == "SAVE10"


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
