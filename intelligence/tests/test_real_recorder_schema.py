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


# --- Phase 4 selector-evidence preservation ---


def test_click_event_with_both_identifiers_preserves_both_as_evidence():
    """
    When Recorder sends the new, independently-captured
    elementHtmlId/elementDataTestId fields (both present), the existing
    selector preference rule still picks data-testid as the PRIMARY
    selector (unchanged), but the non-chosen HTML id must now survive
    as evidence on the generated step rather than being discarded.
    """
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="click",
            timestamp=1003.0,
            pageUrl="https://shop.test/",
            targetTag="button",
            elementHtmlId="checkout-button",
            elementDataTestId="checkout-submit",
            elementText="Checkout",
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-4", events)
    step = generated.steps[0]

    # Primary selector: existing preference rule unchanged.
    assert step.selector == '[data-testid="checkout-submit"]'
    assert step.selector_kind == "data-testid"
    # Evidence: both raw identifiers preserved, verbatim.
    assert step.element_id == "checkout-button"
    assert step.data_testid == "checkout-submit"


def test_fill_event_with_both_identifiers_preserves_both_as_evidence():
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="input_change",
            timestamp=1004.0,
            pageUrl="https://shop.test/search",
            targetTag="input",
            elementHtmlId="search-box",
            elementDataTestId="search-input",
            value="running shoes",
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-5", events)
    step = generated.steps[0]

    assert step.kind == GEN_STEP_FILL
    assert step.selector_kind == "data-testid"
    assert step.element_id == "search-box"
    assert step.data_testid == "search-input"
    assert step.value == "running shoes"


def test_click_event_with_only_html_id_via_new_fields_has_no_fabricated_data_testid():
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="click",
            timestamp=1005.0,
            pageUrl="https://shop.test/",
            targetTag="button",
            elementHtmlId="checkout-button",
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-6", events)
    step = generated.steps[0]

    assert step.selector == "#checkout-button"
    assert step.selector_kind == "id"
    assert step.element_id == "checkout-button"
    assert step.data_testid is None  # never fabricated


def test_legacy_element_id_only_payload_still_produces_no_secondary_evidence():
    """
    Backward compatibility: an older-style event using only the legacy
    single `elementId` field (no new elementHtmlId/elementDataTestId)
    must continue to work exactly as before -- the non-chosen
    identifier is genuinely unknown in this case (Recorder's old
    encoding is inherently lossy), so element_id/data_testid on the
    generated step correctly reflect only what was actually decodable,
    never fabricating the missing one.
    """
    events = [
        RealRecordedEvent(
            id="evt-1",
            type="click",
            timestamp=1006.0,
            pageUrl="https://shop.test/",
            targetTag="button",
            elementId="checkout-button",  # legacy field only
        )
    ]

    generated = generate_test_from_real_recorder_events("journey-7", events)
    step = generated.steps[0]

    assert step.selector == "#checkout-button"
    assert step.selector_kind == "id"
    assert step.element_id == "checkout-button"
    assert step.data_testid is None  # genuinely unknown via the legacy encoding


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


def test_adapter_directly_preserves_both_identifiers_in_raw_element_info():
    """
    Unit-level check on the adapter itself (item 6/7 of the Phase 4
    selector-evidence audit): adapt_real_event() must place BOTH
    identifiers onto LocalRawElementInfo when both are genuinely known,
    not just when observed indirectly through the full generated-test
    pipeline.
    """
    event = RealRecordedEvent(
        id="evt-1",
        type="click",
        timestamp=1007.0,
        pageUrl="https://shop.test/",
        targetTag="button",
        elementHtmlId="checkout-button",
        elementDataTestId="checkout-submit",
    )

    raw_event = adapt_real_event(event)

    assert raw_event.element is not None
    assert raw_event.element.element_id == "checkout-button"
    assert raw_event.element.data_testid == "checkout-submit"


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
