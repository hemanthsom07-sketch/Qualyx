"""
Journey Understanding package — Task 4 milestone.

Contains a deterministic raw-event -> normalized-journey transformation
PROTOTYPE only. See engine.py for the transformation logic,
local_fixtures.py for temporary raw-event input types, and
normalized_journey.py for the temporary normalized output types.

This is NOT the final shared journey contract.
"""

from .engine import understand_journey
from .local_fixtures import (
    LocalRawJourney,
    LocalRawEvent,
    LocalRawElementInfo,
    EVENT_PAGE_LOAD,
    EVENT_CLICK,
    EVENT_INPUT_CHANGE,
    SUPPORTED_EVENT_TYPES,
)
from .normalized_journey import (
    LocalNormalizedJourney,
    LocalJourneyUnderstandingStep,
    LocalNormalizedElement,
    STEP_NAVIGATE,
    STEP_CLICK,
    STEP_FILL,
)
from .recorder_adapter import (
    RealRecordedEvent,
    adapt_real_event,
    adapt_real_journey,
)

__all__ = [
    "understand_journey",
    "LocalRawJourney",
    "LocalRawEvent",
    "LocalRawElementInfo",
    "EVENT_PAGE_LOAD",
    "EVENT_CLICK",
    "EVENT_INPUT_CHANGE",
    "SUPPORTED_EVENT_TYPES",
    "LocalNormalizedJourney",
    "LocalJourneyUnderstandingStep",
    "LocalNormalizedElement",
    "STEP_NAVIGATE",
    "STEP_CLICK",
    "STEP_FILL",
    "RealRecordedEvent",
    "adapt_real_event",
    "adapt_real_journey",
]
