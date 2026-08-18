"""
Healing Engine (Phase 4, Stages B-D)
=====================================

Consumes the REAL, unmodified diagnosis contract
(intelligence.diagnosis.failure_diagnosis.FailureDiagnosisResult /
LocalGeneratedTest) and, where the currently-available evidence
genuinely supports it, proposes and safely applies a selector
replacement. Nothing in this module modifies, reimplements, or
duplicates diagnosis's classification rules -- diagnosis has already
decided has_failure/classification/correlation_established/
generated_step_id before healing ever runs, and this module only
consumes those decisions.

Three deliberately separate, loosely-coupled stages, matching the
approved architecture:

    FailureDiagnosisResult -> eligibility -> candidate -> proposal -> apply

IMPORTANT, GROUNDED IN THE ACTUAL CURRENT REPOSITORY:

Updated for the Phase 4 selector-evidence milestone. Previously (see
git history), Recorder's getStableIdentifier() collapsed an element's
`id`/`data-testid` into a single preferred value, and
LocalGeneratedStep had no field for the non-chosen identifier, so
candidate generation against real data always concluded "no candidate
available." That evidence gap has now been closed:

- Recorder's getStableIdentifiers() (recorder/src/lib/eventCapture.ts,
  distinct from the legacy, still-unchanged getStableIdentifier())
  independently captures BOTH the `id` and `data-testid` attributes
  when both are genuinely present on an element, with neither derived
  from the other and neither fabricated when absent.
- That evidence now survives, additively, through the Backend
  recording schema, the Intelligence adapter/normalization/generation
  pipeline, execution-payload serialization, and stored TestDefinition
  content, into LocalGeneratedStep's `element_id`/`data_testid` fields
  (see test_generation/generated_test.py and
  test_generation/engine.py's _resolve_stable_selector()).
- The real ExecutionResult/FailureEvidence contract
  (intelligence.diagnosis.execution_result) still has no DOM snapshot
  and no list of candidate elements currently on the page -- that
  remains a genuine gap for anything beyond the two identifiers
  Recorder itself can observe at capture time.

Consequently: candidate generation against data actually produced by
today's real Recorder -> Intelligence -> Execution pipeline will now
genuinely find a real candidate whenever the recorded element had both
a real `id` and a real `data-testid` -- and will still honestly report
"no candidate available" when only one was ever known (still the
common case: many elements only have one of the two attributes, and
recordings captured before this milestone only ever have one). Neither
outcome is a fabrication; both are the correct, evidence-based answer
given what's actually known for that element.

No selector is ever guessed from element text. No selector is ever
invented. No DOM is queried. No LLM is used.
"""

from dataclasses import dataclass, field, replace
from typing import Optional

from ..diagnosis.engine import APPLICATION_BUG, BROKEN_TEST, ENVIRONMENT_OR_EXECUTION, UNCERTAIN
from ..diagnosis.failure_diagnosis import FailureDiagnosisResult
from ..test_generation.generated_test import (
    GEN_STEP_CLICK,
    GEN_STEP_FILL,
    LocalGeneratedStep,
    LocalGeneratedTest,
)
from ..test_generation.execution_payload import find_generated_step_by_id

# Step kinds that carry a selector at all. GEN_STEP_NAVIGATE steps have
# a `url`, never a `selector` -- there is structurally nothing to heal
# on a navigate step.
_SELECTOR_BEARING_KINDS = {GEN_STEP_CLICK, GEN_STEP_FILL}

# Selector kinds this module will ever propose or accept. Deliberately
# the exact same two kinds test_generation/engine.py already generates
# (see its selector_kind values) -- healing never introduces a new
# selector strategy of its own.
SELECTOR_KIND_ID = "id"
SELECTOR_KIND_DATA_TESTID = "data-testid"
_VALID_SELECTOR_KINDS = {SELECTOR_KIND_ID, SELECTOR_KIND_DATA_TESTID}


class HealingNotSafeError(Exception):
    """Raised by apply_healing() when a proposal is not safe to apply."""


# ---------------------------------------------------------------------------
# Stage B: eligibility
# ---------------------------------------------------------------------------


@dataclass
class HealingEligibility:
    """
    Typed eligibility decision. Every field here is either copied
    verbatim from the input FailureDiagnosisResult, or a structural
    fact about the correlated step (its kind/selector presence) --
    never a re-classification of the failure itself.
    """
    eligible: bool
    reason: str
    classification: Optional[str] = None  # copied verbatim from diagnosis
    generated_step_id: Optional[str] = None  # copied verbatim from diagnosis


def determine_eligibility(
    diagnosis: FailureDiagnosisResult,
    generated_test: LocalGeneratedTest,
) -> HealingEligibility:
    """
    Deterministic eligibility decision, based only on:
      - diagnosis.has_failure / classification / correlation_established
        / generated_step_id (all real, already-decided fields -- no
        error-text re-parsing, no reimplementation of diagnosis's own
        classification keyword rules)
      - the STRUCTURE of the correlated step (its kind: does it even
        have a selector to heal), looked up via the existing,
        unmodified find_generated_step_by_id()

    Rules (evaluated top to bottom):
      1. No failure                                -> not eligible
      2. APPLICATION_BUG / ENVIRONMENT_OR_EXECUTION -> not eligible
         (diagnosis has already indicated this is not a test-selector
         problem)
      3. Correlation not established (no generated_step_id)
                                                     -> not eligible
         (nothing to safely target)
      4. Classification UNCERTAIN or BROKEN_TEST, correlated, but the
         correlated step doesn't structurally have a selector (a
         navigate step)                             -> not eligible
      5. Classification UNCERTAIN or BROKEN_TEST, correlated, and the
         correlated step is selector-bearing (click/fill) with a real,
         non-empty selector                         -> potentially
                                                        eligible
      6. Any other classification (defensive)       -> not eligible
    """
    if not diagnosis.has_failure:
        return HealingEligibility(
            eligible=False,
            reason="Execution did not fail; there is nothing to heal.",
        )

    if diagnosis.classification in (APPLICATION_BUG, ENVIRONMENT_OR_EXECUTION):
        return HealingEligibility(
            eligible=False,
            reason=(
                f"Diagnosis classified this failure as {diagnosis.classification}, "
                "which is not a test-selector problem. Healing is not applicable."
            ),
            classification=diagnosis.classification,
        )

    if not diagnosis.correlation_established or diagnosis.generated_step_id is None:
        return HealingEligibility(
            eligible=False,
            reason=(
                "The failure could not be correlated to a specific generated "
                "step (correlation_established is False / generated_step_id is "
                "None). There is no specific step to safely target for "
                "healing."
            ),
            classification=diagnosis.classification,
        )

    if diagnosis.classification not in (UNCERTAIN, BROKEN_TEST):
        # Defensive: any future/unrecognized classification is treated
        # as not eligible rather than guessed into eligibility.
        return HealingEligibility(
            eligible=False,
            reason=(
                f"Classification '{diagnosis.classification}' is not one of "
                "the categories healing considers (UNCERTAIN, BROKEN_TEST)."
            ),
            classification=diagnosis.classification,
            generated_step_id=diagnosis.generated_step_id,
        )

    matched_step = find_generated_step_by_id(generated_test, diagnosis.generated_step_id)
    if matched_step is None:
        # Defensive: diagnosis said correlation succeeded, but this
        # generated_test doesn't contain that step id. Never assume --
        # refuse instead.
        return HealingEligibility(
            eligible=False,
            reason=(
                f"generated_step_id '{diagnosis.generated_step_id}' was not "
                "found in the provided generated_test; refusing to guess "
                "which step to target."
            ),
            classification=diagnosis.classification,
            generated_step_id=diagnosis.generated_step_id,
        )

    if matched_step.kind not in _SELECTOR_BEARING_KINDS:
        return HealingEligibility(
            eligible=False,
            reason=(
                f"The correlated step is of type '{matched_step.kind}', which "
                "has no selector to heal (only 'click'/'fill' steps do)."
            ),
            classification=diagnosis.classification,
            generated_step_id=diagnosis.generated_step_id,
        )

    if not matched_step.selector:
        return HealingEligibility(
            eligible=False,
            reason="The correlated step has no recorded selector to heal.",
            classification=diagnosis.classification,
            generated_step_id=diagnosis.generated_step_id,
        )

    return HealingEligibility(
        eligible=True,
        reason=(
            f"Correlated failure on a selector-bearing '{matched_step.kind}' "
            f"step, classified as {diagnosis.classification}. A selector "
            "replacement candidate may be attempted."
        ),
        classification=diagnosis.classification,
        generated_step_id=diagnosis.generated_step_id,
    )


# ---------------------------------------------------------------------------
# Stage C: evidence-backed candidate generation
# ---------------------------------------------------------------------------


@dataclass
class KnownElementIdentifiers:
    """
    All independently-known stable identifiers for the element a step
    targeted. Deliberately a separate type from LocalGeneratedStep:
    LocalGeneratedStep only ever retains the ONE identifier that was
    actually chosen as `selector`/`selector_kind` (see module
    docstring for why real recordings never carry a second one) -- this
    type exists so the underlying candidate-selection algorithm can be
    expressed and tested generically, independent of that real-world
    limitation.
    """
    element_id: Optional[str] = None
    data_testid: Optional[str] = None


@dataclass
class SelectorCandidateResult:
    """Result of attempting to find an alternative, evidence-backed selector."""
    has_candidate: bool
    proposed_selector: Optional[str] = None
    proposed_selector_kind: Optional[str] = None
    reason: str = ""


def _build_selector(kind: str, value: str) -> str:
    """
    Builds a selector string exactly the way
    test_generation/engine.py already does for these same two kinds --
    healing does not introduce a new selector syntax.
    """
    if kind == SELECTOR_KIND_ID:
        return f"#{value}"
    if kind == SELECTOR_KIND_DATA_TESTID:
        return f'[data-testid="{value}"]'
    raise ValueError(f"Unsupported selector kind: {kind}")


def generate_selector_candidate(
    failed_selector_kind: str,
    known_identifiers: KnownElementIdentifiers,
) -> SelectorCandidateResult:
    """
    Deterministic candidate-selection algorithm: if `known_identifiers`
    contains a stable identifier OTHER than the one that just failed,
    propose it. Otherwise, explicitly report no candidate.

    Never guesses from element text (KnownElementIdentifiers has no
    text field at all -- there is nothing to guess from). Never invents
    a selector kind beyond id/data-testid.
    """
    if failed_selector_kind == SELECTOR_KIND_ID:
        if known_identifiers.data_testid:
            return SelectorCandidateResult(
                has_candidate=True,
                proposed_selector=_build_selector(
                    SELECTOR_KIND_DATA_TESTID, known_identifiers.data_testid
                ),
                proposed_selector_kind=SELECTOR_KIND_DATA_TESTID,
                reason=(
                    "A data-testid identifier is independently known for this "
                    "element and differs from the failed id-based selector."
                ),
            )
    elif failed_selector_kind == SELECTOR_KIND_DATA_TESTID:
        if known_identifiers.element_id:
            return SelectorCandidateResult(
                has_candidate=True,
                proposed_selector=_build_selector(
                    SELECTOR_KIND_ID, known_identifiers.element_id
                ),
                proposed_selector_kind=SELECTOR_KIND_ID,
                reason=(
                    "An id identifier is independently known for this element "
                    "and differs from the failed data-testid-based selector."
                ),
            )
    else:
        return SelectorCandidateResult(
            has_candidate=False,
            reason=f"Unrecognized failed selector kind: '{failed_selector_kind}'.",
        )

    return SelectorCandidateResult(
        has_candidate=False,
        reason=(
            "No alternative stable identifier is known for this element. "
            "The current Recorder contract (getStableIdentifier()) captures "
            "only one identifier per element, and no current-DOM re-scan "
            "capability exists, so there is no second piece of evidence to "
            "propose a replacement from."
        ),
    )


def generate_candidate_for_step(matched_step: LocalGeneratedStep) -> SelectorCandidateResult:
    """
    Real-world integration point: builds KnownElementIdentifiers from
    an actual LocalGeneratedStep.

    Phase 4 selector-evidence milestone: LocalGeneratedStep now carries
    `element_id`/`data_testid` as genuine secondary-identifier evidence
    (see test_generation/generated_test.py and
    test_generation/engine.py's _resolve_stable_selector()), populated
    whenever Recorder captured both a real HTML id and a real
    data-testid for the element (see
    recorder/src/lib/eventCapture.ts's getStableIdentifiers()) and that
    evidence survived storage (see
    backend/app/services/diagnosis_client.py's
    _generated_test_from_stored_content()). When only one identifier
    was ever genuinely known -- still the common case for older
    recordings, or any element that only has one of the two attributes
    -- this correctly yields has_candidate=False; no fabrication either
    way.
    """
    if matched_step.selector_kind not in _VALID_SELECTOR_KINDS or not matched_step.selector:
        return SelectorCandidateResult(
            has_candidate=False,
            reason=(
                "The failed step's selector_kind is not one healing "
                "recognizes ('id'/'data-testid'), or no selector is present. "
                "Refusing to propose a candidate rather than guessing."
            ),
        )

    known = KnownElementIdentifiers(
        element_id=matched_step.element_id,
        data_testid=matched_step.data_testid,
    )

    return generate_selector_candidate(matched_step.selector_kind, known)


# ---------------------------------------------------------------------------
# Healing proposal: composes eligibility + candidate generation
# ---------------------------------------------------------------------------


@dataclass
class HealingProposal:
    """
    Typed healing proposal. `proposed_selector`/`proposed_selector_kind`
    are None whenever no evidence-backed candidate exists -- never a
    fabricated placeholder. `safe_to_apply` is the single source of
    truth apply_healing() checks before touching anything.
    """
    eligible: bool
    has_candidate: bool
    safe_to_apply: bool
    reason: str
    generated_step_id: Optional[str] = None  # verbatim from diagnosis
    original_selector: Optional[str] = None  # verbatim from the matched step
    original_selector_kind: Optional[str] = None
    proposed_selector: Optional[str] = None  # never fabricated; None if no candidate
    proposed_selector_kind: Optional[str] = None


def propose_healing(
    diagnosis: FailureDiagnosisResult,
    generated_test: LocalGeneratedTest,
) -> HealingProposal:
    """
    Composes determine_eligibility() and generate_candidate_for_step()
    -- no new decision logic beyond combining their outputs and
    deciding safe_to_apply.
    """
    eligibility = determine_eligibility(diagnosis, generated_test)

    if not eligibility.eligible:
        return HealingProposal(
            eligible=False,
            has_candidate=False,
            safe_to_apply=False,
            reason=eligibility.reason,
            generated_step_id=eligibility.generated_step_id,
        )

    matched_step = find_generated_step_by_id(generated_test, diagnosis.generated_step_id)
    # eligibility.eligible True guarantees matched_step is not None and
    # is selector-bearing with a real selector -- re-fetched here
    # rather than threaded through, to keep determine_eligibility()'s
    # and propose_healing()'s responsibilities cleanly separate.
    assert matched_step is not None and matched_step.selector and matched_step.selector_kind

    candidate = generate_candidate_for_step(matched_step)

    if not candidate.has_candidate:
        return HealingProposal(
            eligible=True,
            has_candidate=False,
            safe_to_apply=False,
            reason=candidate.reason,
            generated_step_id=diagnosis.generated_step_id,
            original_selector=matched_step.selector,
            original_selector_kind=matched_step.selector_kind,
        )

    safe = (
        candidate.proposed_selector is not None
        and candidate.proposed_selector_kind in _VALID_SELECTOR_KINDS
        and candidate.proposed_selector != matched_step.selector
    )

    return HealingProposal(
        eligible=True,
        has_candidate=True,
        safe_to_apply=safe,
        reason=candidate.reason if safe else "Proposed candidate failed a safety check.",
        generated_step_id=diagnosis.generated_step_id,
        original_selector=matched_step.selector,
        original_selector_kind=matched_step.selector_kind,
        proposed_selector=candidate.proposed_selector,
        proposed_selector_kind=candidate.proposed_selector_kind,
    )


# ---------------------------------------------------------------------------
# Stage D: safe, pure application
# ---------------------------------------------------------------------------


def apply_healing(
    generated_test: LocalGeneratedTest,
    proposal: HealingProposal,
) -> LocalGeneratedTest:
    """
    Pure transformation: returns a NEW LocalGeneratedTest with exactly
    the targeted step's selector/selector_kind replaced. The input
    generated_test and all of its step objects other than the targeted
    one are left completely untouched (dataclasses.replace() never
    mutates in place) -- so a caller holding a reference to the
    original generated_test/steps sees no change.

    Refuses (raises HealingNotSafeError) rather than applying anything
    when:
      - proposal.safe_to_apply is not True
      - proposal.generated_step_id is None
      - proposal.proposed_selector / proposed_selector_kind are missing
        or not a recognized kind (defensive re-check, even though
        propose_healing() should never produce such a proposal)
      - the targeted step id does not actually exist in generated_test
        (protects against silently doing nothing, or applying to the
        wrong test)
    """
    if not proposal.safe_to_apply:
        raise HealingNotSafeError(
            f"Refusing to apply: proposal is not marked safe_to_apply. Reason: {proposal.reason}"
        )
    if proposal.generated_step_id is None:
        raise HealingNotSafeError("Refusing to apply: proposal has no generated_step_id to target.")
    if not proposal.proposed_selector or proposal.proposed_selector_kind not in _VALID_SELECTOR_KINDS:
        raise HealingNotSafeError(
            "Refusing to apply: proposed_selector/proposed_selector_kind is missing "
            "or not a recognized kind."
        )

    new_steps: list[LocalGeneratedStep] = []
    target_found = False
    for step in generated_test.steps:
        if step.step_id == proposal.generated_step_id:
            target_found = True
            new_steps.append(
                replace(
                    step,
                    selector=proposal.proposed_selector,
                    selector_kind=proposal.proposed_selector_kind,
                )
            )
        else:
            # Untouched -- same step, not even copied.
            new_steps.append(step)

    if not target_found:
        raise HealingNotSafeError(
            f"Refusing to apply: target step '{proposal.generated_step_id}' was not "
            "found in the provided generated_test."
        )

    return replace(generated_test, steps=new_steps)
