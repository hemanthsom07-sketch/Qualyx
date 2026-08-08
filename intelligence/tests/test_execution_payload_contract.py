"""
Tests for Task 8: Intelligence-side compatibility with the Execution
Engine's failure contract (failedStepId correlation).

Verifies that the exact "id" field the Execution Engine will echo
back as failedStepId matches, byte-for-byte, the deterministic Task 7
step_id -- with no new ID scheme, and no dependency on array position.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from intelligence.journey_understanding.recorder_adapter import RealRecordedEvent
from intelligence.pipeline import (
    generate_test_from_real_recorder_events,
    generate_execution_payload_from_real_recorder_events,
)
from intelligence.test_generation import GEN_STEP_NAVIGATE, GEN_STEP_CLICK, GEN_STEP_FILL
from intelligence.test_generation.execution_payload import (
    to_execution_step_payload,
    to_execution_test_payload,
    find_generated_step_by_id,
)


def _three_step_events():
    return [
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


def test_generated_executable_steps_contain_stable_ids():
    payload = generate_execution_payload_from_real_recorder_events("j1", _three_step_events())
    ids = [s["id"] for s in payload["steps"]]
    assert ids == ["gen-step-rec-evt-1", "gen-step-rec-evt-2", "gen-step-rec-evt-3"]
    for step in payload["steps"]:
        assert "id" in step
        assert step["id"]  # non-empty


def test_execution_payload_ids_deterministic_across_repeated_generation():
    payload_a = generate_execution_payload_from_real_recorder_events("j1", _three_step_events())
    payload_b = generate_execution_payload_from_real_recorder_events("j1", _three_step_events())

    ids_a = [s["id"] for s in payload_a["steps"]]
    ids_b = [s["id"] for s in payload_b["steps"]]
    assert ids_a == ids_b


def test_same_recorder_event_id_produces_same_generated_step_id():
    event = RealRecordedEvent(
        id="rec-evt-x",
        type="click",
        timestamp=1000.0,
        pageUrl="https://shop.test/",
        targetTag="button",
        elementId="checkout-btn",
    )

    payload_a = generate_execution_payload_from_real_recorder_events("j1", [event])
    payload_b = generate_execution_payload_from_real_recorder_events("j2", [event])

    # Same source event -> same step id, even across different journeys.
    assert payload_a["steps"][0]["id"] == payload_b["steps"][0]["id"] == "gen-step-rec-evt-x"


def test_different_recorder_events_produce_different_step_ids():
    payload = generate_execution_payload_from_real_recorder_events("j1", _three_step_events())
    ids = [s["id"] for s in payload["steps"]]
    assert len(ids) == len(set(ids))


def test_ids_survive_full_recorder_to_execution_payload_pipeline():
    generated = generate_test_from_real_recorder_events("j1", _three_step_events())
    payload = to_execution_test_payload(generated)

    # The dataclass step_id and the serialized "id" must match exactly --
    # no transformation of the identifier occurs during serialization.
    for dataclass_step, payload_step in zip(generated.steps, payload["steps"]):
        assert dataclass_step.step_id == payload_step["id"]
        assert dataclass_step.kind == payload_step["type"]


def test_unsupported_events_do_not_receive_generated_ids():
    events = [
        RealRecordedEvent(
            id="rec-evt-1", type="page_load", timestamp=1000.0, pageUrl="https://shop.test/"
        ),
        RealRecordedEvent(
            id="rec-evt-2", type="scroll", timestamp=1000.5, pageUrl="https://shop.test/"
        ),  # unsupported
        RealRecordedEvent(
            id="rec-evt-3",
            type="click",
            timestamp=1001.0,
            pageUrl="https://shop.test/",
            targetTag="button",
            elementId="checkout-btn",
        ),
    ]

    payload = generate_execution_payload_from_real_recorder_events("j1", events)

    ids = [s["id"] for s in payload["steps"]]
    assert ids == ["gen-step-rec-evt-1", "gen-step-rec-evt-3"]
    assert "gen-step-rec-evt-2" not in ids
    assert len(payload["steps"]) == 2  # the scroll event produced no step at all


def test_redacted_input_never_appears_in_execution_payload():
    events = [
        RealRecordedEvent(
            id="rec-evt-1",
            type="input_change",
            timestamp=1000.0,
            pageUrl="https://shop.test/login",
            targetTag="input",
            elementId="password-input",
            value=None,
            redacted=True,
        ),
    ]

    payload = generate_execution_payload_from_real_recorder_events("j1", events)

    # A redacted step must never reach the Execution Engine at all --
    # nothing fabricated, nothing sent.
    assert payload["steps"] == []


def test_generated_step_id_is_exactly_what_execution_engine_should_receive():
    """
    Simulates the round trip Task 8 describes: Intelligence generates a
    step, its "id" is sent to the Execution Engine, and the Execution
    Engine's failedStepId (assumed to simply echo back the id it was
    given, per Claude 2's Task 8 report) is used to look the step back
    up on the Intelligence side.
    """
    generated = generate_test_from_real_recorder_events("j1", _three_step_events())
    payload = to_execution_test_payload(generated)

    # Simulate the Execution Engine reporting a failure on the 2nd step
    # (index 1) by echoing that step's "id" as failedStepId.
    simulated_failed_step_id = payload["steps"][1]["id"]

    matched_step = find_generated_step_by_id(generated, simulated_failed_step_id)

    assert matched_step is not None
    assert matched_step.step_id == simulated_failed_step_id
    assert matched_step.source_event_id == "rec-evt-2"
    assert matched_step.kind == GEN_STEP_CLICK


def test_failed_step_id_lookup_returns_none_when_not_found_or_null():
    generated = generate_test_from_real_recorder_events("j1", _three_step_events())

    assert find_generated_step_by_id(generated, None) is None
    assert find_generated_step_by_id(generated, "does-not-exist") is None


def test_generated_step_ids_do_not_depend_on_array_position():
    """
    Builds two journeys where the same events appear in different
    positions/groupings, and confirms each event's generated step id
    is tied to its own event id/content, not to its index in the list.
    """
    event_a = RealRecordedEvent(
        id="rec-evt-a",
        type="click",
        timestamp=1000.0,
        pageUrl="https://shop.test/",
        targetTag="button",
        elementId="btn-a",
    )
    event_b = RealRecordedEvent(
        id="rec-evt-b",
        type="click",
        timestamp=1001.0,
        pageUrl="https://shop.test/",
        targetTag="button",
        elementId="btn-b",
    )

    payload_ab = generate_execution_payload_from_real_recorder_events(
        "j1", [event_a, event_b]
    )
    payload_ba = generate_execution_payload_from_real_recorder_events(
        "j2", [event_b, event_a]
    )

    ids_by_event_ab = {s["id"]: s for s in payload_ab["steps"]}
    ids_by_event_ba = {s["id"]: s for s in payload_ba["steps"]}

    # event_a's id must be identical whether it's first or second in the list.
    assert "gen-step-rec-evt-a" in ids_by_event_ab
    assert "gen-step-rec-evt-a" in ids_by_event_ba
    assert "gen-step-rec-evt-b" in ids_by_event_ab
    assert "gen-step-rec-evt-b" in ids_by_event_ba

    # Order in the output list changed, but the id assigned to each
    # event's content did not.
    assert [s["id"] for s in payload_ab["steps"]] == ["gen-step-rec-evt-a", "gen-step-rec-evt-b"]
    assert [s["id"] for s in payload_ba["steps"]] == ["gen-step-rec-evt-b", "gen-step-rec-evt-a"]


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