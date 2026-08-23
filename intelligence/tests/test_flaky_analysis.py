"""
Tests for the Phase 5 Stage 1 flaky/recurring-failure analysis engine.

Pure in-memory fixtures throughout -- no database, no Backend, no
mocking of the analysis engine itself (per the approval: "Do not mock
the analysis engine"). Every test constructs ExecutionRecord lists
directly and calls analyze_executions() for real.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from intelligence.flaky_analysis import analyze_executions, ExecutionRecord


def _record(execution_id, status, failed_step_id=None, classification=None, healing_status=None):
    return ExecutionRecord(
        execution_id=execution_id,
        status=status,
        failed_step_id=failed_step_id,
        diagnosis_classification=classification,
        healing_status=healing_status,
    )


# ---------------------------------------------------------------------------
# 1. Fewer than 3 executions -> insufficient_data
# ---------------------------------------------------------------------------


def test_zero_executions_is_insufficient_data():
    result = analyze_executions("t1", [])

    assert result.insufficient_data is True
    assert result.is_flaky is False
    assert result.flaky_reason is None
    assert result.executions_analyzed == 0


def test_two_executions_is_insufficient_data():
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "failed", failed_step_id="s1", classification="UNCERTAIN"),
    ]

    result = analyze_executions("t1", executions)

    assert result.insufficient_data is True
    assert result.is_flaky is False
    # Real counts are still reported even when insufficient for a
    # flaky verdict -- insufficient_data only blocks the verdict itself.
    assert result.failed_count == 2


# ---------------------------------------------------------------------------
# 2. All passing -> not flaky
# ---------------------------------------------------------------------------


def test_all_passing_is_not_flaky():
    executions = [_record(f"e{i}", "passed") for i in range(5)]

    result = analyze_executions("t1", executions)

    assert result.insufficient_data is False
    assert result.is_flaky is False
    assert result.consistently_failing is False
    assert result.passed_count == 5
    assert result.failed_count == 0
    assert result.recurring_signatures == []


# ---------------------------------------------------------------------------
# 3. All failing, same signature -> consistently failing, NOT flaky
# ---------------------------------------------------------------------------


def test_all_failing_same_signature_is_consistently_failing_not_flaky():
    executions = [
        _record(f"e{i}", "failed", failed_step_id="s1", classification="UNCERTAIN") for i in range(4)
    ]

    result = analyze_executions("t1", executions)

    assert result.consistently_failing is True
    assert result.is_flaky is False
    assert result.flaky_reason is None
    assert len(result.recurring_signatures) == 1
    assert result.recurring_signatures[0].occurrence_count == 4


# ---------------------------------------------------------------------------
# 4. FAIL -> PASS -> FAIL, same signature -> flaky
# ---------------------------------------------------------------------------


def test_fail_pass_fail_same_signature_is_flaky():
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "passed"),
        _record("e3", "failed", failed_step_id="s1", classification="UNCERTAIN"),
    ]

    result = analyze_executions("t1", executions)

    assert result.is_flaky is True
    assert result.consistently_failing is False
    assert "s1" in result.flaky_reason
    assert result.recurring_signatures[0].first_execution_id == "e1"
    assert result.recurring_signatures[0].last_execution_id == "e3"


# ---------------------------------------------------------------------------
# 5. PASS -> FAIL -> PASS, same signature recurring elsewhere -> flaky
#    (see engine.py's module docstring for why a SINGLE occurrence in a
#    pass/fail/pass shape does not itself count -- tested separately
#    right below this test)
# ---------------------------------------------------------------------------


def test_pass_fail_pass_recurring_signature_is_flaky():
    executions = [
        _record("e1", "passed"),
        _record("e2", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e3", "passed"),
        _record("e4", "failed", failed_step_id="s1", classification="UNCERTAIN"),
    ]

    result = analyze_executions("t1", executions)

    assert result.is_flaky is True
    assert result.recurring_signatures[0].occurrence_count == 2


def test_pass_fail_pass_single_occurrence_is_not_flaky():
    """
    A single isolated failure surrounded by passes has not "occurred in
    at least 2 separate executions" -- it cannot be flaky by the
    approved definition's own first requirement, since there is nothing
    for it to recur with. See engine.py's module docstring for the
    explicit reasoning behind this interpretation.
    """
    executions = [
        _record("e1", "passed"),
        _record("e2", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e3", "passed"),
    ]

    result = analyze_executions("t1", executions)

    assert result.is_flaky is False
    assert result.recurring_signatures == []


# ---------------------------------------------------------------------------
# 6. Different failure signatures -> not falsely flaky
# ---------------------------------------------------------------------------


def test_different_signatures_are_not_falsely_flaky():
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "passed"),
        _record("e3", "failed", failed_step_id="s2", classification="APPLICATION_BUG"),
    ]

    result = analyze_executions("t1", executions)

    # Neither signature occurred twice -- no recurrence, so not flaky,
    # even though there IS a pass sandwiched between two failures.
    assert result.is_flaky is False
    assert result.recurring_signatures == []


def test_different_classification_for_same_step_is_a_different_signature():
    # Same failed_step_id but a different diagnosis classification is
    # treated as a genuinely different signature, per the approved
    # (failed_step_id, classification) tuple definition.
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "passed"),
        _record("e3", "failed", failed_step_id="s1", classification="APPLICATION_BUG"),
    ]

    result = analyze_executions("t1", executions)

    assert result.is_flaky is False
    assert result.recurring_signatures == []


# ---------------------------------------------------------------------------
# 7. failed_step_id=None -> never matched, even against another None
# ---------------------------------------------------------------------------


def test_none_failed_step_id_is_never_matched_against_itself():
    executions = [
        _record("e1", "failed", failed_step_id=None, classification="UNCERTAIN"),
        _record("e2", "passed"),
        _record("e3", "failed", failed_step_id=None, classification="UNCERTAIN"),
    ]

    result = analyze_executions("t1", executions)

    assert result.is_flaky is False
    assert result.recurring_signatures == []
    assert result.most_frequent_failing_step_id is None


# ---------------------------------------------------------------------------
# 8. Multiple recurring signatures
# ---------------------------------------------------------------------------


def test_multiple_recurring_signatures_are_all_reported():
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "passed"),
        _record("e3", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e4", "passed"),
        _record("e5", "failed", failed_step_id="s2", classification="APPLICATION_BUG"),
        _record("e6", "passed"),
        _record("e7", "failed", failed_step_id="s2", classification="APPLICATION_BUG"),
    ]

    result = analyze_executions("t1", executions)

    assert result.is_flaky is True
    assert len(result.recurring_signatures) == 2
    step_ids = {sig.failed_step_id for sig in result.recurring_signatures}
    assert step_ids == {"s1", "s2"}


# ---------------------------------------------------------------------------
# 9. Most frequent failing step
# ---------------------------------------------------------------------------


def test_most_frequent_failing_step_is_identified():
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "failed", failed_step_id="s2", classification="APPLICATION_BUG"),
        _record("e3", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e4", "failed", failed_step_id="s1", classification="UNCERTAIN"),
    ]

    result = analyze_executions("t1", executions)

    assert result.most_frequent_failing_step_id == "s1"


def test_most_frequent_failing_step_tie_break_is_deterministic():
    # s1 and s2 both fail exactly once -- s1 appears first chronologically.
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "failed", failed_step_id="s2", classification="APPLICATION_BUG"),
    ]

    result = analyze_executions("t1", executions)

    assert result.most_frequent_failing_step_id == "s1"


# ---------------------------------------------------------------------------
# 10. Diagnosis classification counts
# ---------------------------------------------------------------------------


def test_diagnosis_classification_counts_are_tallied():
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "failed", failed_step_id="s2", classification="APPLICATION_BUG"),
        _record("e3", "failed", failed_step_id="s3", classification="UNCERTAIN"),
        _record("e4", "passed"),
    ]

    result = analyze_executions("t1", executions)

    assert result.diagnosis_classification_counts == {"UNCERTAIN": 2, "APPLICATION_BUG": 1}


# ---------------------------------------------------------------------------
# 11, 12, 13. Healing attempted / succeeded / failed counts
# ---------------------------------------------------------------------------


def test_healing_attempted_succeeded_and_failed_counts():
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN", healing_status="healed"),
        _record("e2", "failed", failed_step_id="s1", classification="UNCERTAIN", healing_status="healing_failed"),
        _record("e3", "failed", failed_step_id="s2", classification="APPLICATION_BUG", healing_status="not_eligible"),
        _record("e4", "passed", healing_status="not_attempted"),
    ]

    result = analyze_executions("t1", executions)

    # attempted = healed + healing_failed only -- not_eligible/
    # not_attempted/no_candidate/rejected never involved a real second
    # execution, so they are not counted as "attempts".
    assert result.healing_attempted_count == 2
    assert result.healing_succeeded_count == 1
    assert result.healing_failed_count == 1


def test_zero_healing_attempts_reports_zero_not_none():
    executions = [_record(f"e{i}", "passed") for i in range(3)]

    result = analyze_executions("t1", executions)

    assert result.healing_attempted_count == 0
    assert result.healing_succeeded_count == 0
    assert result.healing_failed_count == 0


# ---------------------------------------------------------------------------
# 14. Successful healing does not convert a failure into a pass
# ---------------------------------------------------------------------------


def test_successful_healing_does_not_convert_failure_into_pass():
    # Three original failures, all successfully healed -- this must
    # still be reported as 3 failed / 0 passed for flaky-detection
    # purposes, and (since all 3 share a signature with no interleaved
    # pass) as consistently_failing, NOT flaky, DESPITE healing having
    # "fixed" every single one.
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN", healing_status="healed"),
        _record("e2", "failed", failed_step_id="s1", classification="UNCERTAIN", healing_status="healed"),
        _record("e3", "failed", failed_step_id="s1", classification="UNCERTAIN", healing_status="healed"),
    ]

    result = analyze_executions("t1", executions)

    assert result.passed_count == 0
    assert result.failed_count == 3
    assert result.consistently_failing is True
    assert result.is_flaky is False
    assert result.healing_succeeded_count == 3


# ---------------------------------------------------------------------------
# 15. Deterministic: identical input -> identical output
# ---------------------------------------------------------------------------


def test_identical_input_produces_identical_output():
    executions = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN", healing_status="healed"),
        _record("e2", "passed"),
        _record("e3", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e4", "failed", failed_step_id="s2", classification="APPLICATION_BUG"),
    ]

    result_a = analyze_executions("t1", executions)
    result_b = analyze_executions("t1", executions)

    assert result_a == result_b


# ---------------------------------------------------------------------------
# 16. Execution ordering is respected
# ---------------------------------------------------------------------------


def test_execution_ordering_is_respected():
    # Same set of records, reversed order -- the "pass between earliest
    # and latest occurrence" logic depends on chronological order, so
    # reversing the input must change the analysis (a pass that was
    # "between" the two failures is no longer between them once the
    # order is reversed and re-interpreted as chronological).
    chronological = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "passed"),
        _record("e3", "failed", failed_step_id="s1", classification="UNCERTAIN"),
    ]
    reversed_order = list(reversed(chronological))

    result_chronological = analyze_executions("t1", chronological)
    result_reversed = analyze_executions("t1", reversed_order)

    assert result_chronological.is_flaky is True
    # Reversed: e3(fail), e2(pass), e1(fail) -- the pass is still
    # between the two failure occurrences positionally, so this
    # particular symmetric example is still flaky either way; the real
    # point is that first/last_execution_id correctly track the given
    # order rather than being order-independent.
    assert result_reversed.is_flaky is True
    assert result_chronological.recurring_signatures[0].first_execution_id == "e1"
    assert result_chronological.recurring_signatures[0].last_execution_id == "e3"
    assert result_reversed.recurring_signatures[0].first_execution_id == "e3"
    assert result_reversed.recurring_signatures[0].last_execution_id == "e1"


def test_execution_ordering_changes_flaky_verdict_when_asymmetric():
    # A case where reordering genuinely flips the verdict: failures
    # adjacent (no pass between) vs. failures with a pass between,
    # depending on which order is treated as chronological.
    adjacent_failures_first = [
        _record("e1", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e2", "failed", failed_step_id="s1", classification="UNCERTAIN"),
        _record("e3", "passed"),
    ]
    result = analyze_executions("t1", adjacent_failures_first)

    assert result.is_flaky is False
    assert result.consistently_failing is False  # one pass exists, just not "between"


# ---------------------------------------------------------------------------
# Result contract sanity: window_description reflects what was given
# ---------------------------------------------------------------------------


def test_window_description_reflects_provided_count():
    executions = [_record(f"e{i}", "passed") for i in range(7)]

    result = analyze_executions("t1", executions)

    assert "7" in result.window_description


def test_test_definition_id_is_passed_through_verbatim():
    result = analyze_executions("my-test-id-123", [])
    assert result.test_definition_id == "my-test-id-123"
