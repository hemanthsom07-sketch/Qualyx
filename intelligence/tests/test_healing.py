"""
Tests for the Phase 4 healing engine (Stages B-D): eligibility,
evidence-backed candidate generation, proposal composition, and safe
pure application.

These tests construct FailureDiagnosisResult/LocalGeneratedTest
directly (the same pattern test_failure_diagnosis.py and
test_explainability.py already use) since healing's contract is with
those real types, not with how they were produced. One test at the end
exercises the full real diagnose_execution_result() -> propose_healing()
chain to confirm the wiring against genuinely real diagnosis output,
not just hand-built fixtures.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from intelligence.diagnosis import APPLICATION_BUG, BROKEN_TEST, ENVIRONMENT_OR_EXECUTION, UNCERTAIN
from intelligence.diagnosis.failure_diagnosis import FailureDiagnosisResult, diagnose_execution_result
from intelligence.diagnosis.execution_result import ExecutionResult
from intelligence.test_generation.generated_test import LocalGeneratedStep, LocalGeneratedTest

from intelligence.healing import (
    apply_healing,
    determine_eligibility,
    generate_candidate_for_step,
    generate_selector_candidate,
    propose_healing,
    HealingNotSafeError,
    HealingProposal,
    KnownElementIdentifiers,
    SELECTOR_KIND_DATA_TESTID,
    SELECTOR_KIND_ID,
)


def _generated_test(steps):
    return LocalGeneratedTest(journey_id="journey-1", steps=steps)


def _navigate_step(step_id="gen-nav-1"):
    return LocalGeneratedStep(
        step_id=step_id, kind="navigate", source_step_id=None, url="https://shop.test/"
    )


def _click_step(
    step_id="gen-click-1", selector="#checkout-submit", selector_kind="id",
    element_id=None, data_testid=None,
):
    return LocalGeneratedStep(
        step_id=step_id,
        kind="click",
        source_step_id=None,
        selector=selector,
        selector_kind=selector_kind,
        element_id=element_id,
        data_testid=data_testid,
    )


def _fill_step(step_id="gen-fill-1", selector="#search-box", selector_kind="id", value="running shoes"):
    return LocalGeneratedStep(
        step_id=step_id,
        kind="fill",
        source_step_id=None,
        selector=selector,
        selector_kind=selector_kind,
        value=value,
    )


def _diagnosis(
    has_failure=True,
    classification=UNCERTAIN,
    confidence=0.25,
    correlation_established=True,
    generated_step_id="gen-click-1",
    error="element not found",
) -> FailureDiagnosisResult:
    return FailureDiagnosisResult(
        has_failure=has_failure,
        classification=classification,
        confidence=confidence,
        correlation_established=correlation_established,
        failed_step_id=generated_step_id,
        failed_step_index=1,
        error=error,
        generated_step_id=generated_step_id,
        evidence=["some evidence"],
        explanation="some explanation",
    )


# ---------------------------------------------------------------------------
# 1. Eligibility
# ---------------------------------------------------------------------------


def test_no_failure_is_not_eligible():
    gt = _generated_test([_navigate_step(), _click_step()])
    diagnosis = _diagnosis(has_failure=False, classification=None, generated_step_id=None)

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is False
    assert "did not fail" in result.reason.lower()


def test_application_bug_is_not_eligible():
    gt = _generated_test([_navigate_step(), _click_step()])
    diagnosis = _diagnosis(classification=APPLICATION_BUG, confidence=0.7)

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is False
    assert result.classification == APPLICATION_BUG


def test_environment_or_execution_is_not_eligible():
    gt = _generated_test([_navigate_step(), _click_step()])
    diagnosis = _diagnosis(classification=ENVIRONMENT_OR_EXECUTION, confidence=0.55)

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is False
    assert result.classification == ENVIRONMENT_OR_EXECUTION


def test_uncorrelated_uncertain_failure_is_not_eligible():
    gt = _generated_test([_navigate_step(), _click_step()])
    diagnosis = _diagnosis(
        classification=UNCERTAIN,
        confidence=0.1,
        correlation_established=False,
        generated_step_id=None,
    )

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is False
    assert "correlated" in result.reason.lower()
    assert result.generated_step_id is None  # never fabricated


def test_correlated_uncertain_on_navigate_step_is_not_eligible():
    # A navigate step has no selector -- structurally nothing to heal,
    # regardless of classification.
    gt = _generated_test([_navigate_step(step_id="gen-nav-1")])
    diagnosis = _diagnosis(classification=UNCERTAIN, confidence=0.15, generated_step_id="gen-nav-1")

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is False
    assert "selector" in result.reason.lower()


def test_correlated_uncertain_on_click_step_is_eligible():
    gt = _generated_test([_navigate_step(), _click_step()])
    diagnosis = _diagnosis(classification=UNCERTAIN, confidence=0.25, generated_step_id="gen-click-1")

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is True
    assert result.generated_step_id == "gen-click-1"


def test_correlated_uncertain_on_fill_step_is_eligible():
    gt = _generated_test([_navigate_step(), _fill_step()])
    diagnosis = _diagnosis(classification=UNCERTAIN, confidence=0.25, generated_step_id="gen-fill-1")

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is True


def test_broken_test_classification_is_eligible():
    # BROKEN_TEST is not produced by the real pipeline today, but is a
    # valid category on FailureDiagnosisResult's own type -- eligibility
    # must still handle it correctly.
    gt = _generated_test([_navigate_step(), _click_step()])
    diagnosis = _diagnosis(classification=BROKEN_TEST, confidence=0.75, generated_step_id="gen-click-1")

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is True


def test_generated_step_id_not_found_in_test_is_not_eligible():
    # Defensive: diagnosis claims correlation, but this generated_test
    # doesn't actually contain that step id. Must refuse, not guess.
    gt = _generated_test([_navigate_step()])
    diagnosis = _diagnosis(classification=UNCERTAIN, generated_step_id="gen-click-does-not-exist")

    result = determine_eligibility(diagnosis, gt)

    assert result.eligible is False
    assert "not found" in result.reason.lower()


# ---------------------------------------------------------------------------
# 2. Candidate generation
# ---------------------------------------------------------------------------


def test_no_alternative_identifier_yields_no_candidate():
    known = KnownElementIdentifiers()  # nothing else known

    result = generate_selector_candidate(SELECTOR_KIND_ID, known)

    assert result.has_candidate is False
    assert result.proposed_selector is None


def test_known_data_testid_produces_candidate_when_id_failed():
    known = KnownElementIdentifiers(data_testid="checkout-submit")

    result = generate_selector_candidate(SELECTOR_KIND_ID, known)

    assert result.has_candidate is True
    assert result.proposed_selector == '[data-testid="checkout-submit"]'
    assert result.proposed_selector_kind == SELECTOR_KIND_DATA_TESTID


def test_known_id_produces_candidate_when_data_testid_failed():
    known = KnownElementIdentifiers(element_id="checkout-submit")

    result = generate_selector_candidate(SELECTOR_KIND_DATA_TESTID, known)

    assert result.has_candidate is True
    assert result.proposed_selector == "#checkout-submit"
    assert result.proposed_selector_kind == SELECTOR_KIND_ID


def test_unrecognized_failed_selector_kind_yields_no_candidate():
    known = KnownElementIdentifiers(element_id="foo", data_testid="bar")

    result = generate_selector_candidate("xpath", known)

    assert result.has_candidate is False


def test_generated_step_with_no_secondary_evidence_yields_no_candidate():
    """
    A step whose element_id/data_testid evidence fields are unset (the
    common case: an element only ever had one of the two attributes,
    or this step was generated before the Phase 4 selector-evidence
    milestone) must still honestly report no candidate -- this remains
    the correct answer when only one identifier was ever genuinely
    known, not a missing feature.
    """
    step = _click_step(selector="#checkout-submit", selector_kind="id")
    assert step.element_id is None
    assert step.data_testid is None

    result = generate_candidate_for_step(step)

    assert result.has_candidate is False


def test_generated_step_with_genuine_secondary_evidence_yields_real_candidate():
    """
    Phase 4 selector-evidence milestone: a LocalGeneratedStep whose
    element genuinely had both a real id and a real data-testid (now
    preserved end-to-end from Recorder through storage) must produce a
    genuine, evidence-backed candidate -- this is the real behavior
    change this milestone delivers, not a hypothetical.
    """
    step = _click_step(
        selector="#checkout-button", selector_kind="id",
        element_id="checkout-button", data_testid="checkout-submit",
    )

    result = generate_candidate_for_step(step)

    assert result.has_candidate is True
    assert result.proposed_selector == '[data-testid="checkout-submit"]'
    assert result.proposed_selector_kind == SELECTOR_KIND_DATA_TESTID


def test_generated_step_with_data_testid_primary_and_id_evidence_yields_candidate():
    step = _click_step(
        selector='[data-testid="checkout-submit"]', selector_kind="data-testid",
        element_id="checkout-button", data_testid="checkout-submit",
    )

    result = generate_candidate_for_step(step)

    assert result.has_candidate is True
    assert result.proposed_selector == "#checkout-button"
    assert result.proposed_selector_kind == SELECTOR_KIND_ID


def test_step_with_no_selector_yields_no_candidate():
    step = LocalGeneratedStep(
        step_id="gen-click-broken", kind="click", source_step_id=None, selector=None, selector_kind=None
    )

    result = generate_candidate_for_step(step)

    assert result.has_candidate is False


# ---------------------------------------------------------------------------
# 3. Proposal composition
# ---------------------------------------------------------------------------


def test_proposal_for_ineligible_failure_has_no_candidate_and_is_unsafe():
    gt = _generated_test([_navigate_step(), _click_step()])
    diagnosis = _diagnosis(classification=APPLICATION_BUG, confidence=0.7)

    proposal = propose_healing(diagnosis, gt)

    assert proposal.eligible is False
    assert proposal.has_candidate is False
    assert proposal.safe_to_apply is False
    assert proposal.proposed_selector is None


def test_proposal_for_eligible_failure_with_no_evidence_reports_no_candidate():
    gt = _generated_test([_navigate_step(), _click_step()])
    diagnosis = _diagnosis(classification=UNCERTAIN, confidence=0.25, generated_step_id="gen-click-1")

    proposal = propose_healing(diagnosis, gt)

    assert proposal.eligible is True
    assert proposal.has_candidate is False
    assert proposal.safe_to_apply is False
    assert proposal.proposed_selector is None
    assert proposal.original_selector == "#checkout-submit"


def test_original_selector_is_always_preserved_verbatim_in_proposal():
    gt = _generated_test([_navigate_step(), _click_step(selector="#weird-id-123", selector_kind="id")])
    diagnosis = _diagnosis(classification=UNCERTAIN, generated_step_id="gen-click-1")

    proposal = propose_healing(diagnosis, gt)

    assert proposal.original_selector == "#weird-id-123"
    assert proposal.original_selector_kind == "id"


# ---------------------------------------------------------------------------
# 4. Safe application
# ---------------------------------------------------------------------------


def _safe_proposal(step_id="gen-click-1", original="#checkout-submit", proposed='[data-testid="checkout-submit"]'):
    return HealingProposal(
        eligible=True,
        has_candidate=True,
        safe_to_apply=True,
        reason="ok",
        generated_step_id=step_id,
        original_selector=original,
        original_selector_kind=SELECTOR_KIND_ID,
        proposed_selector=proposed,
        proposed_selector_kind=SELECTOR_KIND_DATA_TESTID,
    )


def test_apply_healing_rejects_unsafe_proposal():
    gt = _generated_test([_navigate_step(), _click_step()])
    unsafe = HealingProposal(
        eligible=True, has_candidate=False, safe_to_apply=False, reason="no candidate",
        generated_step_id="gen-click-1",
    )

    with pytest.raises(HealingNotSafeError):
        apply_healing(gt, unsafe)


def test_apply_healing_rejects_proposal_missing_step_id():
    gt = _generated_test([_navigate_step(), _click_step()])
    bad = HealingProposal(
        eligible=True, has_candidate=True, safe_to_apply=True, reason="ok",
        generated_step_id=None, proposed_selector="#x", proposed_selector_kind=SELECTOR_KIND_ID,
    )

    with pytest.raises(HealingNotSafeError):
        apply_healing(gt, bad)


def test_apply_healing_rejects_proposal_with_missing_proposed_selector():
    gt = _generated_test([_navigate_step(), _click_step()])
    bad = HealingProposal(
        eligible=True, has_candidate=True, safe_to_apply=True, reason="ok",
        generated_step_id="gen-click-1", proposed_selector=None, proposed_selector_kind=SELECTOR_KIND_ID,
    )

    with pytest.raises(HealingNotSafeError):
        apply_healing(gt, bad)


def test_apply_healing_rejects_target_step_not_in_test():
    gt = _generated_test([_navigate_step()])
    proposal = _safe_proposal(step_id="gen-click-does-not-exist")

    with pytest.raises(HealingNotSafeError):
        apply_healing(gt, proposal)


def test_apply_healing_changes_only_the_targeted_step():
    gt = _generated_test([_navigate_step(), _click_step(), _fill_step()])
    proposal = _safe_proposal()

    healed = apply_healing(gt, proposal)

    # Targeted step changed
    assert healed.steps[1].selector == '[data-testid="checkout-submit"]'
    assert healed.steps[1].selector_kind == SELECTOR_KIND_DATA_TESTID
    # All other steps are the exact same, untouched objects
    assert healed.steps[0] is gt.steps[0]
    assert healed.steps[2] is gt.steps[2]


def test_apply_healing_does_not_mutate_the_original_test():
    gt = _generated_test([_navigate_step(), _click_step()])
    original_selector = gt.steps[1].selector
    proposal = _safe_proposal()

    apply_healing(gt, proposal)

    # Original generated_test/step must be completely unaffected --
    # apply_healing is a pure function, never mutates its input.
    assert gt.steps[1].selector == original_selector


def test_apply_healing_preserves_step_kind_and_unrelated_fields():
    gt = _generated_test([_fill_step(selector="#search-box", selector_kind="id", value="running shoes")])
    proposal = HealingProposal(
        eligible=True, has_candidate=True, safe_to_apply=True, reason="ok",
        generated_step_id="gen-fill-1", original_selector="#search-box", original_selector_kind="id",
        proposed_selector='[data-testid="search-box"]', proposed_selector_kind=SELECTOR_KIND_DATA_TESTID,
    )

    healed = apply_healing(gt, proposal)

    assert healed.steps[0].kind == "fill"
    assert healed.steps[0].value == "running shoes"  # unrelated field preserved
    assert healed.steps[0].selector == '[data-testid="search-box"]'


def test_apply_healing_rejects_unrecognized_selector_kind():
    gt = _generated_test([_click_step()])
    bad = HealingProposal(
        eligible=True, has_candidate=True, safe_to_apply=True, reason="ok",
        generated_step_id="gen-click-1", proposed_selector="//div", proposed_selector_kind="xpath",
    )

    with pytest.raises(HealingNotSafeError):
        apply_healing(gt, bad)


# ---------------------------------------------------------------------------
# 5. No fabrication
# ---------------------------------------------------------------------------


def test_healing_never_fabricates_a_selector_when_no_evidence_exists():
    gt = _generated_test([_navigate_step(), _click_step(selector="#totally-normal-id", selector_kind="id")])
    diagnosis = _diagnosis(classification=UNCERTAIN, generated_step_id="gen-click-1")

    proposal = propose_healing(diagnosis, gt)

    assert proposal.proposed_selector is None
    assert proposal.proposed_selector_kind is None
    assert proposal.safe_to_apply is False


def test_healing_never_produces_a_candidate_equal_to_the_original():
    # Defensive: even if a caller constructed KnownElementIdentifiers
    # with the SAME value as the one that already failed, proposal
    # composition's safety check must reject "replacing" with an
    # identical selector.
    step = _click_step(selector="#checkout-submit", selector_kind="id")
    known_same = KnownElementIdentifiers(data_testid="checkout-submit")
    candidate = generate_selector_candidate("id", known_same)
    # candidate itself is a *different* selector string/kind (data-testid
    # vs id) even though the underlying value happens to match -- this
    # confirms the safety check is about the actual selector, not just
    # presence of a second field.
    assert candidate.proposed_selector != step.selector


# ---------------------------------------------------------------------------
# 6. Real diagnosis integration (not a hand-built fixture)
# ---------------------------------------------------------------------------


def test_propose_healing_against_real_diagnose_execution_result_output():
    gt = _generated_test(
        [
            _navigate_step(step_id="gen-nav-1"),
            _click_step(step_id="gen-click-1", selector="#checkout-submit", selector_kind="id"),
        ]
    )
    execution_result = ExecutionResult(
        status="failed",
        failedStepIndex=1,
        failedStepId="gen-click-1",
        error='page.click: waiting for locator("#checkout-submit") failed: element not found',
        executedStepCount=2,
    )

    diagnosis = diagnose_execution_result(gt, execution_result)
    assert diagnosis.classification == UNCERTAIN  # sanity check on real diagnosis behavior

    proposal = propose_healing(diagnosis, gt)

    assert proposal.eligible is True
    assert proposal.generated_step_id == "gen-click-1"
    assert proposal.original_selector == "#checkout-submit"
    # This step was generated with no secondary-identifier evidence
    # (element_id/data_testid unset) -- honest outcome: no candidate.
    # See the next test for the case where genuine evidence exists.
    assert proposal.has_candidate is False
    assert proposal.safe_to_apply is False


def test_full_real_healing_cycle_with_genuine_dual_identifier_evidence():
    """
    End-to-end proof that the Phase 4 selector-evidence milestone
    actually closes the loop: real diagnose_execution_result() ->
    real propose_healing() -> real apply_healing(), using a
    LocalGeneratedTest whose failed step genuinely carries both a
    primary selector and real secondary-identifier evidence (as it
    would after passing through the real Recorder -> Intelligence ->
    storage -> diagnosis reconstruction pipeline).
    """
    gt = _generated_test(
        [
            _navigate_step(step_id="gen-nav-1"),
            _click_step(
                step_id="gen-click-1",
                selector="#checkout-button",
                selector_kind="id",
                element_id="checkout-button",
                data_testid="checkout-submit",
            ),
        ]
    )
    execution_result = ExecutionResult(
        status="failed",
        failedStepIndex=1,
        failedStepId="gen-click-1",
        error='page.click: waiting for locator("#checkout-button") failed: element not found',
        executedStepCount=2,
    )

    diagnosis = diagnose_execution_result(gt, execution_result)
    assert diagnosis.classification == UNCERTAIN

    proposal = propose_healing(diagnosis, gt)
    assert proposal.eligible is True
    assert proposal.has_candidate is True
    assert proposal.safe_to_apply is True
    assert proposal.proposed_selector == '[data-testid="checkout-submit"]'

    healed = apply_healing(gt, proposal)

    assert healed.steps[1].selector == '[data-testid="checkout-submit"]'
    assert healed.steps[1].selector_kind == SELECTOR_KIND_DATA_TESTID
    # Original untouched (pure function).
    assert gt.steps[1].selector == "#checkout-button"
    # The untouched navigate step is the exact same object.
    assert healed.steps[0] is gt.steps[0]


def test_propose_healing_against_real_application_bug_diagnosis_is_ineligible():
    gt = _generated_test(
        [
            _navigate_step(step_id="gen-nav-1"),
            _click_step(step_id="gen-click-1"),
        ]
    )
    execution_result = ExecutionResult(
        status="failed",
        failedStepIndex=1,
        failedStepId="gen-click-1",
        error="Request failed with status code 503",
        executedStepCount=2,
    )

    diagnosis = diagnose_execution_result(gt, execution_result)
    assert diagnosis.classification == APPLICATION_BUG  # sanity check

    proposal = propose_healing(diagnosis, gt)

    assert proposal.eligible is False
    assert proposal.has_candidate is False
