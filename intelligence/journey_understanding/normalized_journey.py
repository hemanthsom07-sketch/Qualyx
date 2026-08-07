"""
LOCAL PROTOTYPE OUTPUT TYPES — NOT A SHARED CONTRACT
======================================================

Normalized journey representation produced by the journey-understanding
prototype. Deliberately minimal; not the final shared journey/test
contract. These are consumed internally by the test-generation
prototype in this same milestone.
"""

from dataclasses import dataclass, field
from typing import Optional


# Normalized step kinds for this milestone.
STEP_NAVIGATE = "navigate"
STEP_CLICK = "click"
STEP_FILL = "fill"


@dataclass
class LocalNormalizedElement:
    """Normalized, minimal element reference carried forward from a raw event."""
    tag: Optional[str] = None
    role: Optional[str] = None
    text: Optional[str] = None
    element_id: Optional[str] = None
    data_testid: Optional[str] = None
    css_selector: Optional[str] = None


@dataclass
class LocalJourneyUnderstandingStep:
    """One normalized, meaningful journey step."""
    step_id: str
    kind: str  # STEP_NAVIGATE / STEP_CLICK / STEP_FILL
    source_event_id: str  # traceability back to the raw event, no fabrication
    url: Optional[str] = None
    element: Optional[LocalNormalizedElement] = None
    value: Optional[str] = None  # only for STEP_FILL
    redacted: bool = False  # true if the source event's value was withheld by the Recorder


@dataclass
class LocalNormalizedJourney:
    """Ordered set of normalized journey steps plus a record of skipped events."""
    journey_id: str
    steps: list[LocalJourneyUnderstandingStep] = field(default_factory=list)
    skipped_event_ids: list[str] = field(default_factory=list)
