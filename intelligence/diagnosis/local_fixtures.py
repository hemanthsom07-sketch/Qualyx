"""
LOCAL PROTOTYPE FIXTURES — NOT A SHARED CONTRACT
==================================================

These types exist ONLY to exercise the diagnosis prototype for the
Task 3 milestone. They are intentionally minimal, internal to
/intelligence, and MUST NOT be imported by, or treated as, the
canonical shared contracts (RecordedJourney, ExecutionResult,
FailureDiagnosis) that will eventually live in /shared/contracts.

Once the real shared contracts are frozen by all three developers,
these local types should be deleted/replaced — they are scaffolding,
not an API surface.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LocalElementInfo:
    """Minimal element description used only by this prototype."""
    tag: Optional[str] = None
    role: Optional[str] = None
    text: Optional[str] = None
    selector: Optional[str] = None


@dataclass
class LocalJourneyStep:
    """One step of a locally-defined sample recorded journey."""
    step_id: str
    action_type: str  # e.g. "click", "fill", "navigate"
    element: Optional[LocalElementInfo] = None


@dataclass
class LocalRecordedJourney:
    """A minimal stand-in for a recorded journey, local to this prototype."""
    journey_id: str
    steps: list[LocalJourneyStep] = field(default_factory=list)
    # Elements observed to currently exist on the page at failure time,
    # used to check whether a similar element is still present.
    current_dom_elements: list[LocalElementInfo] = field(default_factory=list)


@dataclass
class LocalExecutionFailure:
    """A minimal stand-in for an execution failure result."""
    run_id: str
    failed_step_id: str
    error_type: str          # e.g. "SELECTOR_NOT_FOUND", "HTTP_ERROR", "TIMEOUT"
    error_message: str = ""
    http_status: Optional[int] = None
    attempted_selector: Optional[str] = None
