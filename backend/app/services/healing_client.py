"""
Backend <-> Intelligence healing boundary (Phase 4 Stage E).

Mirrors diagnosis_client.py's pattern exactly: Intelligence's healing
module is a plain, dependency-free Python package living as a sibling
directory, so this is an in-process composition boundary, not a
subprocess. The sys.path bootstrap below is the same idempotent pattern
diagnosis_client.py already uses -- repeated here (not imported from
there) so this module has no import-order dependency on
diagnosis_client.py having run first.

This module contains NO healing decision logic of its own -- it only:
  1. Reconstructs the LocalGeneratedTest representation from stored
     TestDefinition content, by calling diagnosis_client.py's own
     _generated_test_from_stored_content() a second time (per the
     approved Stage E design: rebuild rather than widen
     diagnose_and_explain()'s return contract, which every existing
     diagnosis test already depends on).
  2. Calls the existing, unmodified intelligence.healing functions
     (propose_healing(), which itself composes determine_eligibility(),
     and apply_healing()) -- intelligence/healing/engine.py is not
     modified by this milestone.
  3. Serializes a healed LocalGeneratedTest back into the exact dict
     shape execute_steps() expects, reusing Intelligence's existing,
     unmodified to_execution_test_payload() serializer -- no new
     serialization logic.
  4. Composes a proposal (and, when available, a second execution
     result) into a single HealingAttemptResult for the API response.

Stage E's actual re-execution (the second execute_steps() call) is
deliberately NOT performed here -- it stays owned exclusively by the
route (app/api/routes/test_definitions.py), exactly where the first
execute_steps() call already lives, keeping the Execution Engine
subprocess boundary in exactly one place. prepare_healing_attempt()
only ever prepares what a caller would need to attempt that second
execution; it never calls execute_steps() itself, never persists
anything, and never attempts more than the one healing cycle per call
(there is no loop anywhere in this module).
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from intelligence.diagnosis.failure_diagnosis import FailureDiagnosisResult  # noqa: E402
from intelligence.healing import apply_healing, propose_healing, HealingProposal  # noqa: E402
from intelligence.test_generation.execution_payload import to_execution_test_payload  # noqa: E402

from app.schemas.execution import ExecutionResultOut
from app.services.diagnosis_client import _generated_test_from_stored_content

# Result status values. Exactly the six the Phase 4 Stage E audit
# specified -- no additional states invented.
HEALING_NOT_ATTEMPTED = "not_attempted"
HEALING_NOT_ELIGIBLE = "not_eligible"
HEALING_NO_CANDIDATE = "no_candidate"
HEALING_REJECTED = "rejected"
HEALING_HEALED = "healed"
HEALING_FAILED = "healing_failed"


@dataclass
class HealingAttemptResult:
    """
    Typed healing outcome for a single /execute request. Every field
    here is either copied verbatim from the real HealingProposal (see
    intelligence/healing/engine.py, unmodified), copied verbatim from
    the real diagnosis, or -- for `healed_execution` only -- the real
    ExecutionResultOut from an actual second execute_steps() call.
    Nothing is fabricated.

    `status` is HEALING_HEALED if and only if `applied` is True AND the
    second execution's status was "passed" -- healing is never reported
    as successful without a real, verified second execution.
    """
    status: str
    reason: str
    generated_step_id: Optional[str] = None
    original_selector: Optional[str] = None
    original_selector_kind: Optional[str] = None
    proposed_selector: Optional[str] = None
    proposed_selector_kind: Optional[str] = None
    applied: bool = False
    confidence: Optional[float] = None
    healed_execution: Optional[ExecutionResultOut] = None


def not_attempted_result() -> HealingAttemptResult:
    """Used by the route when diagnosis.has_failure is False -- nothing to heal."""
    return HealingAttemptResult(
        status=HEALING_NOT_ATTEMPTED,
        reason="Execution did not fail; healing was not attempted.",
    )


def prepare_healing_attempt(
    test_definition_id: str,
    content: list[dict],
    diagnosis: FailureDiagnosisResult,
) -> tuple[HealingProposal, Optional[list[dict]]]:
    """
    Reconstructs the generated test from stored content and runs the
    existing, unmodified propose_healing() (which itself calls
    determine_eligibility() internally -- not duplicated here).

    Only when the resulting proposal is safe_to_apply does this
    function actually call apply_healing() and serialize the result.
    Returns (proposal, healed_steps): healed_steps is None whenever
    safe_to_apply is False (not eligible, no candidate, or a rejected/
    unsafe candidate) -- the caller (the route) must not attempt a
    second execute_steps() call in that case.
    """
    generated_test = _generated_test_from_stored_content(test_definition_id, content)
    proposal = propose_healing(diagnosis, generated_test)

    if not proposal.safe_to_apply:
        return proposal, None

    healed_test = apply_healing(generated_test, proposal)
    healed_payload = to_execution_test_payload(healed_test)
    return proposal, healed_payload["steps"]


def build_healing_result(
    diagnosis: FailureDiagnosisResult,
    proposal: HealingProposal,
    healed_execution: Optional[ExecutionResultOut] = None,
) -> HealingAttemptResult:
    """
    Composes a final HealingAttemptResult from a proposal and (only
    when one was actually attempted) a real second execution result.
    No new decision logic beyond mapping the proposal's own fields
    (eligible / has_candidate / safe_to_apply, all decided by
    intelligence.healing, unmodified) onto the six result states.
    """
    if not proposal.eligible:
        return HealingAttemptResult(
            status=HEALING_NOT_ELIGIBLE,
            reason=proposal.reason,
            generated_step_id=proposal.generated_step_id,
            confidence=diagnosis.confidence,
        )

    if not proposal.has_candidate:
        return HealingAttemptResult(
            status=HEALING_NO_CANDIDATE,
            reason=proposal.reason,
            generated_step_id=proposal.generated_step_id,
            original_selector=proposal.original_selector,
            original_selector_kind=proposal.original_selector_kind,
            confidence=diagnosis.confidence,
        )

    if not proposal.safe_to_apply:
        return HealingAttemptResult(
            status=HEALING_REJECTED,
            reason=proposal.reason,
            generated_step_id=proposal.generated_step_id,
            original_selector=proposal.original_selector,
            original_selector_kind=proposal.original_selector_kind,
            proposed_selector=proposal.proposed_selector,
            proposed_selector_kind=proposal.proposed_selector_kind,
            confidence=diagnosis.confidence,
        )

    # safe_to_apply True: a second execution must have genuinely been
    # attempted by the caller before reaching this branch.
    assert healed_execution is not None, (
        "build_healing_result() was called with a safe_to_apply proposal "
        "but no healed_execution -- the caller must execute_steps() the "
        "healed steps before building the final result."
    )

    healed = healed_execution.status == "passed"
    return HealingAttemptResult(
        status=HEALING_HEALED if healed else HEALING_FAILED,
        reason=(
            "The proposed replacement selector was applied and the healed "
            "execution passed."
            if healed
            else "The proposed replacement selector was applied, but the "
            "healed execution still failed."
        ),
        generated_step_id=proposal.generated_step_id,
        original_selector=proposal.original_selector,
        original_selector_kind=proposal.original_selector_kind,
        proposed_selector=proposal.proposed_selector,
        proposed_selector_kind=proposal.proposed_selector_kind,
        applied=True,
        confidence=diagnosis.confidence,
        healed_execution=healed_execution,
    )
