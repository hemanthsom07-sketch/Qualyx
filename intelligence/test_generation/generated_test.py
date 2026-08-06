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
    """One deterministically generated test step."""
    step_id: str
    kind: str  # GEN_STEP_NAVIGATE / GEN_STEP_CLICK / GEN_STEP_FILL
    source_step_id: str  # traceability back to the normalized journey step
    url: Optional[str] = None
    selector: Optional[str] = None
    selector_kind: Optional[str] = None  # "data-testid" / "id" (only stable kinds)
    value: Optional[str] = None  # only for GEN_STEP_FILL


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
