"""
Execution Payload Serialization (Task 8)
===========================================

Claude 2's Execution Engine (Task 8, confirmed complete) expects
executable steps shaped like:

    {
      "steps": [
        { "id": "stable-generated-id", "type": "click", ... }
      ]
    }

and returns:

    {
      "failedStepIndex": 1,
      "failedStepId": "stable-generated-id"
    }

This module is a pure serialization layer on top of the existing,
unmodified Task 7 generated-step model (LocalGeneratedStep /
LocalGeneratedTest). It does not change how step_id is computed --
see test_generation/generated_test.py and journey_understanding/engine.py
for that (Task 7, unchanged). It only maps the internal field names
to the exact keys the Execution Engine's contract requires:

    LocalGeneratedStep.step_id -> "id"    (canonical correlation key)
    LocalGeneratedStep.kind    -> "type"

"id" here IS the same deterministic value produced in Task 7 -- no new
ID scheme, no random/UUID/timestamp values, nothing derived from array
position. This is why `failedStepId` returned by the Execution Engine
can be matched directly, by equality, against the "id" field of one of
the steps in this payload to recover the originating LocalGeneratedStep.

Only steps that were successfully generated (LocalGeneratedTest.steps)
are included -- ungeneratable steps are never sent to the Execution
Engine, since there is nothing safe to execute for them.
"""

from typing import Optional

from .generated_test import LocalGeneratedStep, LocalGeneratedTest


def to_execution_step_payload(step: LocalGeneratedStep) -> dict:
    """
    Serializes one generated step into the exact shape the Execution
    Engine expects for a single step. "id" is step.step_id verbatim --
    the same deterministic, Task-7 stable ID -- with no transformation.
    """
    payload = {
        "id": step.step_id,
        "type": step.kind,
    }
    if step.url is not None:
        payload["url"] = step.url
    if step.selector is not None:
        payload["selector"] = step.selector
    if step.selector_kind is not None:
        payload["selectorKind"] = step.selector_kind
    if step.value is not None:
        payload["value"] = step.value
    return payload


def to_execution_test_payload(generated_test: LocalGeneratedTest) -> dict:
    """
    Serializes a full generated test into the Execution Engine's
    expected request shape: {"steps": [...]}. Only successfully
    generated steps are included, in the same order they were
    produced (order-preserving, per Task 4/7 guarantees).
    """
    return {
        "journeyId": generated_test.journey_id,
        "steps": [to_execution_step_payload(s) for s in generated_test.steps],
    }


def find_generated_step_by_id(
    generated_test: LocalGeneratedTest, step_id: Optional[str]
) -> Optional[LocalGeneratedStep]:
    """
    Given a `failedStepId` value returned by the Execution Engine,
    finds the matching LocalGeneratedStep by exact id equality. This
    is the correlation function described in the Task 8 contract:
    Recorder event -> Intelligence generated step -> Execution Engine
    StepResult -> failedStepId -> (this lookup) -> back to the
    generated step (and, via its source_event_id/source_step_id, back
    to the originating Recorder event).

    Returns None if step_id is None (Execution Engine found no id to
    report, e.g. a legacy un-id'd step) or if no match is found --
    never guesses or falls back to array position.
    """
    if step_id is None:
        return None
    for step in generated_test.steps:
        if step.step_id == step_id:
            return step
    return None