"""
End-to-end tests for the Task 5 pipeline:
    Recorder events -> Journey Understanding -> Test Generation

Uses realistic-shaped recorder events (page_load / click / input_change,
with data-testid / element id / css_selector fields) to validate the
full composed pipeline, on top of the already-tested Task 4 stages.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from intelligence.pipeline import generate_test_from_recorded_events
from intelligence.journey_understanding.local_fixtures import (
    LocalRawJourney,
    LocalRawEvent,
    LocalRawElementInfo,
    EVENT_PAGE_LOAD,
    EVENT_CLICK,
    EVENT_INPUT_CHANGE,
)
from intelligence.test_generation import GEN_STEP_NAVIGATE, GEN_STEP_CLICK, GEN_STEP_FILL


def test_realistic_login_journey_produces_ordered_playwright_ready_steps():
    """
    Simulates a realistic recorded login journey:
    page load -> fill username -> fill password (redacted) -> click sign in
    """
    raw = LocalRawJourney(
        journey_id="journey-login",
        events=[
            LocalRawEvent(
                event_id="evt-1",
                event_type=EVENT_PAGE_LOAD,
                url="https://shop.test/login",
            ),
            LocalRawEvent(
                event_id="evt-2",
                event_type=EVENT_INPUT_CHANGE,
                url="https://shop.test/login",
                element=LocalRawElementInfo(
                    tag="input", data_testid="username-input"
                ),
                input_value="jane.doe@example.com",
            ),
            LocalRawEvent(
                event_id="evt-3",
                event_type=EVENT_INPUT_CHANGE,
                url="https://shop.test/login",
                element=LocalRawElementInfo(
                    tag="input", data_testid="password-input"
                ),
                # Recorder already redacted this before it reached Intelligence.
                input_value="[REDACTED]",
            ),
            LocalRawEvent(
                event_id="evt-4",
                event_type=EVENT_CLICK,
                url="https://shop.test/login",
                element=LocalRawElementInfo(
                    tag="button", role="button", text="Sign In", data_testid="signin-button"
                ),
            ),
        ],
    )

    generated = generate_test_from_recorded_events(raw)

    assert [s.kind for s in generated.steps] == [
        GEN_STEP_NAVIGATE,
        GEN_STEP_FILL,
        GEN_STEP_FILL,
        GEN_STEP_CLICK,
    ]
    assert generated.ungeneratable_steps == []

    navigate_step, username_step, password_step, click_step = generated.steps

    assert navigate_step.url == "https://shop.test/login"

    assert username_step.selector == '[data-testid="username-input"]'
    assert username_step.value == "jane.doe@example.com"

    # Redacted value passed through unchanged -- never reconstructed or altered.
    assert password_step.selector == '[data-testid="password-input"]'
    assert password_step.value == "[REDACTED]"

    assert click_step.selector == '[data-testid="signin-button"]'


def test_selectors_are_directly_usable_playwright_locator_strings():
    raw = LocalRawJourney(
        journey_id="journey-selectors",
        events=[
            LocalRawEvent(
                event_id="evt-1",
                event_type=EVENT_CLICK,
                element=LocalRawElementInfo(tag="button", data_testid="add-to-cart"),
            ),
            LocalRawEvent(
                event_id="evt-2",
                event_type=EVENT_CLICK,
                element=LocalRawElementInfo(tag="button", element_id="checkout-btn"),
            ),
        ],
    )

    generated = generate_test_from_recorded_events(raw)

    # These strings must be usable directly as Playwright locators, e.g.
    # page.locator(selector) / page.click(selector).
    assert generated.steps[0].selector == '[data-testid="add-to-cart"]'
    assert generated.steps[1].selector == "#checkout-btn"


def test_pipeline_never_guesses_a_selector_when_none_is_stable():
    raw = LocalRawJourney(
        journey_id="journey-no-selector",
        events=[
            LocalRawEvent(
                event_id="evt-1",
                event_type=EVENT_CLICK,
                element=LocalRawElementInfo(
                    tag="div", text="Click here", css_selector=".promo-banner > div:nth-child(2)"
                ),
                # No data-testid, no element_id -- only an unstable css_selector.
            ),
        ],
    )

    generated = generate_test_from_recorded_events(raw)

    assert generated.steps == []
    assert len(generated.ungeneratable_steps) == 1
    assert "stable selector" in generated.ungeneratable_steps[0].reason


def test_pipeline_preserves_order_and_skips_unsupported_events_safely():
    raw = LocalRawJourney(
        journey_id="journey-mixed",
        events=[
            LocalRawEvent(event_id="evt-1", event_type=EVENT_PAGE_LOAD, url="https://shop.test/"),
            LocalRawEvent(event_id="evt-2", event_type="mousemove"),  # unsupported
            LocalRawEvent(
                event_id="evt-3",
                event_type=EVENT_CLICK,
                element=LocalRawElementInfo(tag="a", data_testid="nav-products"),
            ),
            LocalRawEvent(event_id="evt-4", event_type="scroll"),  # unsupported
            LocalRawEvent(
                event_id="evt-5",
                event_type=EVENT_INPUT_CHANGE,
                element=LocalRawElementInfo(tag="input", element_id="promo-code"),
                input_value="SAVE10",
            ),
        ],
    )

    generated = generate_test_from_recorded_events(raw)

    assert [s.source_step_id for s in generated.steps] == [
        "step-evt-1",
        "step-evt-3",
        "step-evt-5",
    ]
    assert generated.steps[2].value == "SAVE10"


def test_pipeline_reports_navigate_step_missing_url_without_guessing():
    raw = LocalRawJourney(
        journey_id="journey-bad-nav",
        events=[
            LocalRawEvent(event_id="evt-1", event_type=EVENT_PAGE_LOAD, url=None),
        ],
    )

    generated = generate_test_from_recorded_events(raw)

    assert generated.steps == []
    assert len(generated.ungeneratable_steps) == 1
    assert "URL" in generated.ungeneratable_steps[0].reason


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
