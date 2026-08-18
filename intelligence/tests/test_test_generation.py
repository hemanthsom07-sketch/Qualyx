"""
Focused tests for the Task 4 deterministic test-generation prototype.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from intelligence.journey_understanding import (
    understand_journey,
    LocalRawJourney,
    LocalRawEvent,
    LocalRawElementInfo,
    EVENT_PAGE_LOAD,
    EVENT_CLICK,
    EVENT_INPUT_CHANGE,
)
from intelligence.journey_understanding.normalized_journey import (
    LocalNormalizedJourney,
    LocalJourneyUnderstandingStep,
    LocalNormalizedElement,
    STEP_NAVIGATE,
    STEP_CLICK,
    STEP_FILL,
)
from intelligence.test_generation import (
    generate_test,
    GEN_STEP_NAVIGATE,
    GEN_STEP_CLICK,
    GEN_STEP_FILL,
)


def test_full_normalized_journey_generates_ordered_steps():
    raw = LocalRawJourney(
        journey_id="journey-1",
        events=[
            LocalRawEvent(event_id="e1", event_type=EVENT_PAGE_LOAD, url="https://shop.test/"),
            LocalRawEvent(
                event_id="e2",
                event_type=EVENT_INPUT_CHANGE,
                element=LocalRawElementInfo(tag="input", element_id="search-box"),
                input_value="running shoes",
            ),
            LocalRawEvent(
                event_id="e3",
                event_type=EVENT_CLICK,
                element=LocalRawElementInfo(tag="button", data_testid="add-to-cart"),
            ),
        ],
    )
    normalized = understand_journey(raw)

    generated = generate_test(normalized)

    assert [s.kind for s in generated.steps] == [GEN_STEP_NAVIGATE, GEN_STEP_FILL, GEN_STEP_CLICK]
    assert generated.ungeneratable_steps == []


def test_click_step_prefers_data_testid_over_id():
    step = LocalJourneyUnderstandingStep(
        step_id="s1",
        kind=STEP_CLICK,
        source_event_id="e1",
        element=LocalNormalizedElement(element_id="fallback-id", data_testid="preferred-testid"),
    )
    normalized = LocalNormalizedJourney(journey_id="j1", steps=[step])

    generated = generate_test(normalized)

    assert len(generated.steps) == 1
    assert generated.steps[0].selector_kind == "data-testid"
    assert generated.steps[0].selector == '[data-testid="preferred-testid"]'


def test_click_step_falls_back_to_id_when_no_testid():
    step = LocalJourneyUnderstandingStep(
        step_id="s1",
        kind=STEP_CLICK,
        source_event_id="e1",
        element=LocalNormalizedElement(element_id="login-btn"),
    )
    normalized = LocalNormalizedJourney(journey_id="j1", steps=[step])

    generated = generate_test(normalized)

    assert generated.steps[0].selector_kind == "id"
    assert generated.steps[0].selector == "#login-btn"


def test_fill_step_includes_value_and_selector():
    step = LocalJourneyUnderstandingStep(
        step_id="s1",
        kind=STEP_FILL,
        source_event_id="e1",
        element=LocalNormalizedElement(data_testid="search-box"),
        value="running shoes",
    )
    normalized = LocalNormalizedJourney(journey_id="j1", steps=[step])

    generated = generate_test(normalized)

    assert generated.steps[0].kind == GEN_STEP_FILL
    assert generated.steps[0].value == "running shoes"
    assert generated.steps[0].selector == '[data-testid="search-box"]'


def test_click_step_without_stable_selector_is_not_guessed():
    step = LocalJourneyUnderstandingStep(
        step_id="s1",
        kind=STEP_CLICK,
        source_event_id="e1",
        element=LocalNormalizedElement(tag="button", text="Add to cart"),  # no id/testid
    )
    normalized = LocalNormalizedJourney(journey_id="j1", steps=[step])

    generated = generate_test(normalized)

    assert generated.steps == []
    assert len(generated.ungeneratable_steps) == 1
    assert generated.ungeneratable_steps[0].source_step_id == "s1"
    assert "stable selector" in generated.ungeneratable_steps[0].reason


def test_navigate_step_without_url_is_reported_ungeneratable():
    step = LocalJourneyUnderstandingStep(
        step_id="s1", kind=STEP_NAVIGATE, source_event_id="e1", url=None
    )
    normalized = LocalNormalizedJourney(journey_id="j1", steps=[step])

    generated = generate_test(normalized)

    assert generated.steps == []
    assert len(generated.ungeneratable_steps) == 1
    assert "URL" in generated.ungeneratable_steps[0].reason


def test_generated_step_ordering_matches_normalized_journey_order_including_skips():
    steps = [
        LocalJourneyUnderstandingStep(
            step_id="s1", kind=STEP_NAVIGATE, source_event_id="e1", url="https://shop.test/"
        ),
        LocalJourneyUnderstandingStep(
            step_id="s2",
            kind=STEP_CLICK,
            source_event_id="e2",
            element=LocalNormalizedElement(text="no selector here"),  # ungeneratable
        ),
        LocalJourneyUnderstandingStep(
            step_id="s3",
            kind=STEP_CLICK,
            source_event_id="e3",
            element=LocalNormalizedElement(data_testid="checkout-btn"),
        ),
    ]
    normalized = LocalNormalizedJourney(journey_id="j1", steps=steps)

    generated = generate_test(normalized)

    assert [s.source_step_id for s in generated.steps] == ["s1", "s3"]
    assert [u.source_step_id for u in generated.ungeneratable_steps] == ["s2"]


def test_click_step_prefers_data_testid_but_preserves_element_id_as_evidence():
    """
    Phase 4 selector-evidence milestone (item 9 of the audit): when
    both a data-testid and an element id are known, the existing
    preference rule still chooses data-testid as the primary selector
    (unchanged), but the non-chosen element_id must now survive on
    LocalGeneratedStep as evidence, rather than being discarded.
    """
    journey = LocalNormalizedJourney(
        journey_id="j1",
        steps=[
            LocalJourneyUnderstandingStep(
                step_id="s1",
                kind=STEP_CLICK,
                source_event_id="e1",
                element=LocalNormalizedElement(
                    tag="button",
                    element_id="checkout-button",
                    data_testid="checkout-submit",
                ),
            ),
        ],
    )

    generated = generate_test(journey)
    step = generated.steps[0]

    assert step.selector == '[data-testid="checkout-submit"]'
    assert step.selector_kind == "data-testid"
    assert step.element_id == "checkout-button"
    assert step.data_testid == "checkout-submit"


def test_click_step_with_only_id_has_no_fabricated_data_testid_evidence():
    journey = LocalNormalizedJourney(
        journey_id="j1",
        steps=[
            LocalJourneyUnderstandingStep(
                step_id="s1",
                kind=STEP_CLICK,
                source_event_id="e1",
                element=LocalNormalizedElement(tag="button", element_id="checkout-button"),
            ),
        ],
    )

    generated = generate_test(journey)
    step = generated.steps[0]

    assert step.selector == "#checkout-button"
    assert step.selector_kind == "id"
    assert step.element_id == "checkout-button"
    assert step.data_testid is None


if __name__ == "__main__":
    # Plain-Python runner so this suite works even without pytest installed.
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
