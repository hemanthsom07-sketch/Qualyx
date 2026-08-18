"""
LOCAL PROTOTYPE OUTPUT TYPES — NOT A SHARED CONTRACT
======================================================

Minimal generated-test representation produced by the test-generation
prototype. Deliberately simple so it *could* eventually be consumed by
Claude 2's execution engine, but this is NOT the frozen shared
TestDefinition contract, and no such contract is being created here.
"""

from dataclasses import dataclass, field
from typing import Optional


# Generated step kinds for this milestone.
GEN_STEP_NAVIGATE = "navigate"
GEN_STEP_CLICK = "click"
GEN_STEP_FILL = "fill"


@dataclass
class LocalGeneratedStep:
    """
    One deterministically generated test step.

    Stable ID design (Task 7):
    step_id is deterministic, derived from the source Recorder event's
    real id via the chain:
        raw_event.event_id -> normalized step_id ("step-{event_id}")
        -> this step_id ("gen-{normalized step_id}")
    It contains no random UUIDs, no timestamps, and is not based on
    array position alone (position is only used as part of a
    documented fallback in journey_understanding.engine when a source
    event has no usable id -- see _resolve_step_id_source there).

    source_event_id is carried through directly from the original
    Recorder event (see journey_understanding.local_fixtures /
    recorder_adapter) so a generated step can be mapped straight back
    to the Recorder event that produced it, without requiring a
    separate lookup through the normalized journey step.

    Phase 4 selector-evidence milestone: element_id/data_testid carry
    the RAW stable identifiers that were genuinely known for this
    step's element -- both, if both were genuinely present -- as
    evidence alongside the already-chosen `selector`/`selector_kind`.
    This is not a duplicate selector: `selector`/`selector_kind` remain
    the single, existing-preference-rule-chosen value the Execution
    Engine actually uses; `element_id`/`data_testid` exist purely so
    Healing can later know the non-chosen identifier still genuinely
    existed, instead of it being silently discarded. Never fabricated:
    a field here is populated only when the corresponding raw
    identifier was genuinely known for this element (see
    test_generation/engine.py's _resolve_stable_selector()).
    """
    step_id: str
    kind: str  # GEN_STEP_NAVIGATE / GEN_STEP_CLICK / GEN_STEP_FILL
    source_step_id: str  # traceability back to the normalized journey step
    source_event_id: Optional[str] = None  # traceability back to the raw Recorder event id
    url: Optional[str] = None
    selector: Optional[str] = None
    selector_kind: Optional[str] = None  # "data-testid" / "id" (only stable kinds)
    value: Optional[str] = None  # only for GEN_STEP_FILL
    element_id: Optional[str] = None  # raw HTML id, if genuinely known (selector evidence)
    data_testid: Optional[str] = None  # raw data-testid, if genuinely known (selector evidence)


@dataclass
class LocalUngeneratableStep:
    """A journey step that could not be safely converted, with a reason."""
    source_step_id: str
    reason: str


@dataclass
class LocalGeneratedTest:
    """Ordered set of generated steps, plus any steps that could not be generated."""
    journey_id: str
    steps: list[LocalGeneratedStep] = field(default_factory=list)
    ungeneratable_steps: list[LocalUngeneratableStep] = field(default_factory=list)