"""
LOCAL PROTOTYPE FIXTURES — NOT A SHARED CONTRACT
==================================================

These types represent a minimal stand-in for "raw recorded browser
events" as they might eventually arrive from Claude 1's Recorder,
via the future RecordedJourney shared contract.

They exist ONLY to exercise the journey-understanding prototype for
this milestone. They are intentionally minimal, internal to
/intelligence, and MUST NOT be treated as the canonical shared
contract. Once /shared/contracts is frozen for RecordedJourney,
these should be replaced.
"""

from dataclasses import dataclass, field
from typing import Optional


# Supported raw event types for this milestone.
EVENT_PAGE_LOAD = "page_load"
EVENT_CLICK = "click"
EVENT_INPUT_CHANGE = "input_change"

SUPPORTED_EVENT_TYPES = {EVENT_PAGE_LOAD, EVENT_CLICK, EVENT_INPUT_CHANGE}


@dataclass
class LocalRawElementInfo:
    """Minimal raw element description as it might arrive from Recorder."""
    tag: Optional[str] = None
    role: Optional[str] = None
    text: Optional[str] = None
    element_id: Optional[str] = None       # HTML id attribute
    data_testid: Optional[str] = None      # data-testid attribute
    css_selector: Optional[str] = None     # fallback selector, if any


@dataclass
class LocalRawEvent:
    """One raw recorded browser event, local to this prototype."""
    event_id: str
    event_type: str  # one of SUPPORTED_EVENT_TYPES, or something unsupported
    timestamp: Optional[str] = None
    url: Optional[str] = None
    element: Optional[LocalRawElementInfo] = None
    input_value: Optional[str] = None  # only relevant for input_change
    redacted: bool = False  # true if the Recorder withheld the real value


@dataclass
class LocalRawJourney:
    """A minimal stand-in for a raw recorded journey, local to this prototype."""
    journey_id: str
    events: list[LocalRawEvent] = field(default_factory=list)
