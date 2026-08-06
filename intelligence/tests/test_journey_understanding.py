"""
Focused tests for the Task 4 deterministic journey-understanding prototype.
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
    STEP_NAVIGATE,
    STEP_CLICK,
    STEP_FILL,
)


def test_full_event_sequence_produces_normalized_journey_in_order():
    raw = LocalRawJourney(
        journey_id="journey-1",
        events=[
            LocalRawEvent(event_id="e1", event_type=EVENT_PAGE_LOAD, url="https://shop.test/"),
            LocalRawEvent(
                event_id="e2",
                event_type=EVENT_INPUT_CHANGE,
                url="https://shop.test/",
                element=LocalRawElementInfo(tag="input", element_id="search-box"),
                input_value="running shoes",
            ),
            LocalRawEvent(
                event_id="e3",
                event_type=EVENT_CLICK,
                url="https://shop.test/search",
                element=LocalRawElementInfo(
                    tag="a", role="link", text="Product A", data_testid="product-a"
                ),
            ),
            LocalRawEvent(
                event_id="e4",
                event_type=EVENT_CLICK,
                url="https://shop.test/product/a",
                element=LocalRawElementInfo(
                    tag="button", role="button", text="Add to cart", data_testid="add-to-cart"
                ),
            ),
        ],
    )

    result = understand_journey(raw)

    assert [s.kind for s in result.steps] == [STEP_NAVIGATE, STEP_FILL, STEP_CLICK, STEP_CLICK]
    assert [s.source_event_id for s in result.steps] == ["e1", "e2", "e3", "e4"]
    assert result.skipped_event_ids == []


def test_navigation_event_converts_to_navigate_step_with_url():
    raw = LocalRawJourney(
        journey_id="journey-2",
        events=[LocalRawEvent(event_id="e1", event_type=EVENT_PAGE_LOAD, url="https://shop.test/")],
    )

    result = understand_journey(raw)

    assert len(result.steps) == 1
    step = result.steps[0]
    assert step.kind == STEP_NAVIGATE
    assert step.url == "https://shop.test/"
    assert step.element is None


def test_click_event_converts_with_stable_selector_info_preserved():
    raw = LocalRawJourney(
        journey_id="journey-3",
        events=[
            LocalRawEvent(
                event_id="e1",
                event_type=EVENT_CLICK,
                url="https://shop.test/",
                element=LocalRawElementInfo(
                    tag="button", role="button", text="Add to cart", data_testid="add-to-cart"
                ),
            )
        ],
    )

    result = understand_journey(raw)

    step = result.steps[0]
    assert step.kind == STEP_CLICK
    assert step.element.data_testid == "add-to-cart"
    assert step.element.text == "Add to cart"


def test_fill_event_converts_with_value_preserved():
    raw = LocalRawJourney(
        journey_id="journey-4",
        events=[
            LocalRawEvent(
                event_id="e1",
                event_type=EVENT_INPUT_CHANGE,
                url="https://shop.test/",
                element=LocalRawElementInfo(tag="input", element_id="search-box"),
                input_value="running shoes",
            )
        ],
    )

    result = understand_journey(raw)

    step = result.steps[0]
    assert step.kind == STEP_FILL
    assert step.value == "running shoes"
    assert step.element.element_id == "search-box"


def test_unsupported_event_type_is_safely_skipped_not_guessed():
    raw = LocalRawJourney(
        journey_id="journey-5",
        events=[
            LocalRawEvent(event_id="e1", event_type=EVENT_PAGE_LOAD, url="https://shop.test/"),
            LocalRawEvent(event_id="e2", event_type="scroll", url="https://shop.test/"),
            LocalRawEvent(
                event_id="e3",
                event_type=EVENT_CLICK,
                url="https://shop.test/",
                element=LocalRawElementInfo(tag="button", data_testid="btn"),
            ),
        ],
    )

    result = understand_journey(raw)

    assert [s.source_event_id for s in result.steps] == ["e1", "e3"]
    assert result.skipped_event_ids == ["e2"]


def test_event_order_is_preserved_even_with_skips_interleaved():
    raw = LocalRawJourney(
        journey_id="journey-6",
        events=[
            LocalRawEvent(event_id="e1", event_type="mouseover"),
            LocalRawEvent(event_id="e2", event_type=EVENT_PAGE_LOAD, url="https://shop.test/"),
            LocalRawEvent(event_id="e3", event_type="resize"),
            LocalRawEvent(
                event_id="e4",
                event_type=EVENT_CLICK,
                element=LocalRawElementInfo(tag="button", data_testid="go"),
            ),
        ],
    )

    result = understand_journey(raw)

    assert [s.source_event_id for s in result.steps] == ["e2", "e4"]
    assert result.skipped_event_ids == ["e1", "e3"]


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
