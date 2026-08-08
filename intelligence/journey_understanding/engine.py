"""
Deterministic Journey Understanding Prototype
===============================================

Milestone scope (Task 4): convert a raw locally-defined sequence of
recorded browser events into a simplified, ordered, normalized journey
representation. No LLM, no embeddings, no semantic segmentation, no
behavioral analytics.

Supported raw event types (see local_fixtures.py):
- page_load        -> normalized STEP_NAVIGATE
- click             -> normalized STEP_CLICK
- input_change      -> normalized STEP_FILL

Any other/unsupported event type is safely ignored (recorded in
skipped_event_ids) rather than causing an error or being guessed at.

No intent is fabricated: every normalized step's fields are copied
directly from the corresponding raw event's fields, nothing invented.
"""

from .local_fixtures import (
    LocalRawJourney,
    LocalRawEvent,
    EVENT_PAGE_LOAD,
    EVENT_CLICK,
    EVENT_INPUT_CHANGE,
)
from .normalized_journey import (
    LocalNormalizedJourney,
    LocalJourneyUnderstandingStep,
    LocalNormalizedElement,
    STEP_NAVIGATE,
    STEP_CLICK,
    STEP_FILL,
)


def _normalize_element(raw_event: LocalRawEvent) -> LocalNormalizedElement | None:
    if raw_event.element is None:
        return None
    e = raw_event.element
    return LocalNormalizedElement(
        tag=e.tag,
        role=e.role,
        text=e.text,
        element_id=e.element_id,
        data_testid=e.data_testid,
        css_selector=e.css_selector,
    )


def _resolve_step_id_source(raw_event: LocalRawEvent, index: int) -> str:
    """
    Returns the identifier used to build this step's deterministic
    step_id. Prefers the real Recorder event id (raw_event.event_id).

    Fallback (only when raw_event.event_id is missing/empty): a
    deterministic value derived from this event's position in the
    journey and its event type -- never random, never timestamp-based.
    This fallback is NOT presented as a real Recorder event id; it
    exists solely so step_id stays deterministic and unique even if
    an event somehow arrives without one. raw_event.event_id itself
    (see source_event_id on the normalized step) is left untouched --
    still whatever the raw event actually had, including empty/None --
    so nothing is fabricated as if it came from the Recorder.
    """
    if raw_event.event_id:
        return raw_event.event_id
    return f"noid-idx{index}-{raw_event.event_type}"


def understand_journey(raw_journey: LocalRawJourney) -> LocalNormalizedJourney:
    """
    Deterministically transform a raw event sequence into a normalized
    journey. Event order is preserved. Unsupported events are skipped
    safely (tracked, not dropped silently) rather than guessed at.

    Each normalized step's step_id is deterministic: derived from the
    source event's real id where available (see _resolve_step_id_source
    for the fallback used when it is not).
    """
    normalized_steps: list[LocalJourneyUnderstandingStep] = []
    skipped_event_ids: list[str] = []

    for index, raw_event in enumerate(raw_journey.events):
        if raw_event.event_type == EVENT_PAGE_LOAD:
            normalized_steps.append(
                LocalJourneyUnderstandingStep(
                    step_id=f"step-{_resolve_step_id_source(raw_event, index)}",
                    kind=STEP_NAVIGATE,
                    source_event_id=raw_event.event_id,
                    url=raw_event.url,
                    element=None,
                )
            )

        elif raw_event.event_type == EVENT_CLICK:
            normalized_steps.append(
                LocalJourneyUnderstandingStep(
                    step_id=f"step-{_resolve_step_id_source(raw_event, index)}",
                    kind=STEP_CLICK,
                    source_event_id=raw_event.event_id,
                    url=raw_event.url,
                    element=_normalize_element(raw_event),
                )
            )

        elif raw_event.event_type == EVENT_INPUT_CHANGE:
            normalized_steps.append(
                LocalJourneyUnderstandingStep(
                    step_id=f"step-{_resolve_step_id_source(raw_event, index)}",
                    kind=STEP_FILL,
                    source_event_id=raw_event.event_id,
                    url=raw_event.url,
                    element=_normalize_element(raw_event),
                    value=raw_event.input_value,
                    redacted=raw_event.redacted,
                )
            )

        else:
            # Unsupported/irrelevant event type for this milestone.
            # Safely ignored, but tracked for transparency -- not fabricated,
            # not silently dropped without a trace.
            skipped_event_ids.append(raw_event.event_id)

    return LocalNormalizedJourney(
        journey_id=raw_journey.journey_id,
        steps=normalized_steps,
        skipped_event_ids=skipped_event_ids,
    )