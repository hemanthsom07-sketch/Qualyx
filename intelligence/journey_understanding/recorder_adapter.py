"""
Real Recorder Schema Adapter (Task 5 correction)
===================================================

Converts the ACTUAL Recorder event contract, as inspected directly in
recorder/src/lib/eventCapture.ts, into the already-tested Task 4
pipeline's input types (LocalRawEvent / LocalRawJourney). This is a
pure translation layer: it adds no new classification or generation
logic and does not modify journey_understanding/engine.py or
test_generation/engine.py's core behavior.

Real RecordedEvent contract (from recorder/src/lib/eventCapture.ts):

    {
      id: string;
      type: "page_load" | "click" | "input_change";
      timestamp: number;
      pageUrl: string;
      targetTag?: string;
      elementId?: string;
      elementText?: string;
      value?: string;
      redacted?: boolean;
    }

Stable-selector encoding (from Recorder's getStableIdentifier()):
    - real HTML id            -> elementId = "my-id"
    - data-testid attribute   -> elementId = "data-testid:my-test-id"
    - neither available       -> elementId is undefined/None

This adapter decodes that encoding into the existing element fields
(element_id vs data_testid) that test_generation/engine.py already
knows how to turn into Playwright selectors:
    "my-id"                    -> element_id="my-id"      -> "#my-id"
    "data-testid:my-test-id"   -> data_testid="my-test-id" -> '[data-testid="my-test-id"]'
    None                       -> neither set -> refused, never guessed

Sensitive input handling:
    - Recorder sends value=None (undefined) and redacted=True for
      sensitive fields.
    - This adapter passes that through exactly: input_value stays
      None, redacted stays True. No placeholder value (e.g. the
      string "[REDACTED]") is invented here or anywhere downstream --
      that string is not part of the real Recorder contract, so
      fabricating it would violate the "never fabricate evidence /
      never invent values" principle.
"""

from dataclasses import dataclass
from typing import Optional, Literal

from .local_fixtures import (
    LocalRawJourney,
    LocalRawEvent,
    LocalRawElementInfo,
)

DATA_TESTID_PREFIX = "data-testid:"


@dataclass
class RealRecordedEvent:
    """
    Mirrors the actual Recorder RecordedEvent contract exactly
    (recorder/src/lib/eventCapture.ts). Field names and optionality
    match the real TypeScript interface as inspected; this dataclass
    is a Python-side read-only view of that contract for use inside
    Intelligence, not a redefinition of it.
    """
    id: str
    type: Literal["page_load", "click", "input_change"]
    timestamp: float
    pageUrl: str
    targetTag: Optional[str] = None
    elementId: Optional[str] = None
    elementText: Optional[str] = None
    value: Optional[str] = None
    redacted: Optional[bool] = None


def _decode_stable_identifier(element_id: Optional[str]):
    """
    Decodes Recorder's getStableIdentifier() encoding into
    (element_id, data_testid). Never guesses: if elementId is missing,
    both are None and no selector will later be generated for this
    element.
    """
    if element_id is None:
        return None, None
    if element_id.startswith(DATA_TESTID_PREFIX):
        return None, element_id[len(DATA_TESTID_PREFIX):]
    return element_id, None


def _adapt_element(event: RealRecordedEvent) -> Optional[LocalRawElementInfo]:
    # An "element" is only meaningful for click/input_change events with
    # some element-related data present.
    if event.targetTag is None and event.elementId is None and event.elementText is None:
        return None

    resolved_element_id, resolved_data_testid = _decode_stable_identifier(event.elementId)

    return LocalRawElementInfo(
        tag=event.targetTag,
        role=None,  # not present in the real Recorder contract
        text=event.elementText,
        element_id=resolved_element_id,
        data_testid=resolved_data_testid,
        css_selector=None,  # not present in the real Recorder contract
    )


def adapt_real_event(event: RealRecordedEvent) -> LocalRawEvent:
    """
    Translates one real RecordedEvent into the prototype's LocalRawEvent,
    with no invented fields. redacted defaults to False only when the
    real contract omits it (Recorder's `redacted?: boolean` optional
    field), matching "absence of the flag means not redacted".
    """
    return LocalRawEvent(
        event_id=event.id,
        event_type=event.type,
        timestamp=str(event.timestamp) if event.timestamp is not None else None,
        url=event.pageUrl,
        element=_adapt_element(event),
        input_value=event.value,
        redacted=bool(event.redacted),
    )


def adapt_real_journey(journey_id: str, events: list[RealRecordedEvent]) -> LocalRawJourney:
    """Translates an ordered list of real RecordedEvents into a LocalRawJourney."""
    return LocalRawJourney(
        journey_id=journey_id,
        events=[adapt_real_event(e) for e in events],
    )
