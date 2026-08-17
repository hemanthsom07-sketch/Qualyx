"""
Healing package (Phase 4, Stages B-D).

Consumes the real diagnosis.failure_diagnosis.FailureDiagnosisResult
and produces a deterministic eligibility decision, an evidence-backed
selector-replacement proposal (explicitly "no candidate available" when
the current repository's evidence doesn't support one), and a safe,
pure apply function. See engine.py's module docstring for the full
architecture and the concrete evidence-availability finding this stage
is built against.

No DOM inspection, no text-based selector guessing, no LLM, no
automatic re-execution (that is a later, not-yet-approved stage).
"""

from .engine import (
    apply_healing,
    determine_eligibility,
    generate_candidate_for_step,
    generate_selector_candidate,
    propose_healing,
    HealingEligibility,
    HealingNotSafeError,
    HealingProposal,
    KnownElementIdentifiers,
    SelectorCandidateResult,
    SELECTOR_KIND_DATA_TESTID,
    SELECTOR_KIND_ID,
)

__all__ = [
    "apply_healing",
    "determine_eligibility",
    "generate_candidate_for_step",
    "generate_selector_candidate",
    "propose_healing",
    "HealingEligibility",
    "HealingNotSafeError",
    "HealingProposal",
    "KnownElementIdentifiers",
    "SelectorCandidateResult",
    "SELECTOR_KIND_DATA_TESTID",
    "SELECTOR_KIND_ID",
]
