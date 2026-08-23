"""
Flaky/Recurring-Failure Analysis Engine (Phase 5, Stage 1)
============================================================

Consumes a chronologically-ordered list of historical execution
records and produces a deterministic, explainable FlakyAnalysisResult.
This module is intentionally pure: it does NOT import SQLAlchemy, does
NOT import anything from `backend`, and does NOT touch a database --
callers (a future Backend boundary, in a later, not-yet-approved stage)
are responsible for translating their own stored rows into
ExecutionRecord before calling analyze_executions().

APPROVED SPECIFICATION (Phase 5 Stage 1 approval):

Flaky definition:
  - At least 3 executions are available (otherwise insufficient_data).
  - The same failure signature occurs in at least 2 separate executions.
  - At least one PASS occurs chronologically between the earliest and
    latest occurrence of that signature.
  FAIL, FAIL, FAIL             -> consistently failing, NOT flaky.
  FAIL, PASS, FAIL (same sig)  -> flaky.
  PASS, FAIL, PASS (same sig)  -> flaky IF the same signature recurs
    elsewhere too (a single failure occurrence, by definition, has not
    "occurred in at least 2 separate executions" -- see the module-level
    note below on this specific interpretation).

Failure signature (approved, first version):
    (failed_step_id, diagnosis_classification)
  computed ONLY when failed_step_id is not None. A None failed_step_id
  is never matched against anything, including another None -- it is
  simply excluded from signature-based grouping entirely (uncorrelated
  failures are not assumed to be "the same" as each other).

Healing interpretation (approved):
  Flakiness is determined from each execution's ORIGINAL status only.
  A failure that healing later fixed is still counted as a failure for
  flaky-detection purposes. Healing statistics are reported as
  separate, adjacent facts, never folded into pass/fail counts.

A NOTE ON THE "PASS, FAIL, PASS" EXAMPLE IN THE APPROVAL:
The approval's own wording is "flaky IF the same failure signature
recurs" -- a conditional. Taken together with the flaky definition's
own first requirement ("the same failure signature occurs in at least
2 separate executions"), a single isolated failure surrounded by passes
does NOT itself satisfy "recurs" -- recurrence requires a second
occurrence of that exact signature somewhere in the window. This
module implements that strict, internally-consistent reading: a
lone PASS/FAIL/PASS with only one failure occurrence is NOT flaky by
itself (see test_pass_fail_pass_single_occurrence_is_not_flaky), while
a signature appearing 2+ times with a pass between its earliest and
latest occurrence IS flaky (see
test_fail_pass_fail_same_signature_is_flaky and
test_pass_fail_pass_recurring_signature_is_flaky, which adds a further
occurrence to make the recurrence genuine). This interpretation is
flagged explicitly here and in the Stage 1 delivery report rather than
silently assumed.
"""

from dataclasses import dataclass, field
from typing import Optional

MIN_EXECUTIONS_FOR_ANALYSIS = 3
MIN_OCCURRENCES_TO_RECUR = 2

STATUS_PASSED = "passed"
STATUS_FAILED = "failed"

HEALING_HEALED = "healed"
HEALING_FAILED = "healing_failed"


@dataclass
class ExecutionRecord:
    """
    Minimal, Intelligence-owned view of one historical execution --
    deliberately NOT app.models.execution_run.ExecutionRun or any
    SQLAlchemy type. A future Backend boundary is responsible for
    building these from real ExecutionRun rows.

    ORDERING CONTRACT: the list passed to analyze_executions() MUST be
    in chronological order, OLDEST FIRST. This is what lets "a pass
    between the earliest and latest occurrence of a signature" be a
    simple index comparison. Note that the existing
    GET /tests/{test_id}/executions endpoint returns newest-first
    (matching GET /projects/{project_id}/tests's own convention) -- a
    future Backend boundary calling this engine will need to reverse
    that ordering first. Not addressed here, since that Backend
    boundary is out of scope for Stage 1.
    """
    execution_id: str
    status: str  # STATUS_PASSED / STATUS_FAILED -- mirrors ExecutionRun.status verbatim
    failed_step_id: Optional[str] = None  # mirrors ExecutionRun.failed_step_id verbatim
    diagnosis_classification: Optional[str] = None  # mirrors diagnosis["classification"] verbatim
    healing_status: Optional[str] = None  # mirrors healing["status"] verbatim


FailureSignature = tuple[str, Optional[str]]  # (failed_step_id, diagnosis_classification)


@dataclass
class RecurringSignature:
    """One failure pattern that recurred at least MIN_OCCURRENCES_TO_RECUR times."""
    failed_step_id: str
    classification: Optional[str]
    occurrence_count: int
    first_execution_id: str
    last_execution_id: str


@dataclass
class FlakyAnalysisResult:
    """
    Deterministic, explainable analysis result. Every field is either a
    verbatim count/id drawn from the input ExecutionRecords, or a
    boolean/string mechanically derived from them -- no confidence
    score, no fabricated evidence, no LLM involvement.
    """
    test_definition_id: str
    executions_analyzed: int
    window_description: str
    insufficient_data: bool

    passed_count: int
    failed_count: int

    is_flaky: bool
    flaky_reason: Optional[str]
    consistently_failing: bool

    recurring_signatures: list[RecurringSignature] = field(default_factory=list)
    most_frequent_failing_step_id: Optional[str] = None
    diagnosis_classification_counts: dict[str, int] = field(default_factory=dict)

    healing_attempted_count: int = 0
    healing_succeeded_count: int = 0
    healing_failed_count: int = 0

    evidence: list[str] = field(default_factory=list)


def _failure_signature(record: ExecutionRecord) -> Optional[FailureSignature]:
    """
    A None failed_step_id is never matched against anything -- not even
    another None -- so it always returns None here (excluded from
    signature grouping entirely), never fabricating a shared identity
    for uncorrelated failures.
    """
    if record.failed_step_id is None:
        return None
    return (record.failed_step_id, record.diagnosis_classification)


def analyze_executions(
    test_definition_id: str,
    executions: list[ExecutionRecord],
) -> FlakyAnalysisResult:
    """
    Pure, deterministic analysis. See module docstring for the approved
    flaky/recurring-failure definitions this implements. Identical
    input always produces an identical, equal result (no wall-clock
    reads, no randomness, no set-ordering dependence -- iteration order
    over signatures is the chronological order of first occurrence).
    """
    executions_analyzed = len(executions)
    window_description = f"{executions_analyzed} execution(s) provided"
    insufficient_data = executions_analyzed < MIN_EXECUTIONS_FOR_ANALYSIS

    passed_count = sum(1 for e in executions if e.status == STATUS_PASSED)
    failed_count = sum(1 for e in executions if e.status == STATUS_FAILED)

    # Group failure signatures by first-occurrence order (dicts preserve
    # insertion order in Python -- this is what keeps tie-breaking and
    # iteration deterministic below).
    occurrences: dict[FailureSignature, list[int]] = {}
    for index, record in enumerate(executions):
        if record.status != STATUS_FAILED:
            continue
        signature = _failure_signature(record)
        if signature is None:
            continue
        occurrences.setdefault(signature, []).append(index)

    recurring_signatures: list[RecurringSignature] = []
    flaky_signature_reasons: list[str] = []

    for signature, indices in occurrences.items():
        occurrence_count = len(indices)
        if occurrence_count < MIN_OCCURRENCES_TO_RECUR:
            continue

        failed_step_id, classification = signature
        first_index, last_index = indices[0], indices[-1]
        recurring_signatures.append(
            RecurringSignature(
                failed_step_id=failed_step_id,
                classification=classification,
                occurrence_count=occurrence_count,
                first_execution_id=executions[first_index].execution_id,
                last_execution_id=executions[last_index].execution_id,
            )
        )

        has_pass_between = any(
            executions[i].status == STATUS_PASSED for i in range(first_index + 1, last_index)
        )
        if has_pass_between:
            flaky_signature_reasons.append(
                f"Step '{failed_step_id}' failed as "
                f"{classification!r} in {occurrence_count} of {executions_analyzed} "
                f"executions, with a passing execution between "
                f"'{executions[first_index].execution_id}' and "
                f"'{executions[last_index].execution_id}'."
            )

    is_flaky = (not insufficient_data) and len(flaky_signature_reasons) > 0
    flaky_reason = " ".join(flaky_signature_reasons) if is_flaky else None

    consistently_failing = executions_analyzed > 0 and failed_count == executions_analyzed

    # Most frequent failing step, across ALL failures (not just
    # recurring signatures) -- ties broken by first-occurrence order,
    # via max()'s "first strictly-greatest wins" behavior over an
    # insertion-ordered dict.
    step_failure_counts: dict[str, int] = {}
    for record in executions:
        if record.status == STATUS_FAILED and record.failed_step_id is not None:
            step_failure_counts[record.failed_step_id] = (
                step_failure_counts.get(record.failed_step_id, 0) + 1
            )
    most_frequent_failing_step_id = (
        max(step_failure_counts, key=lambda step_id: step_failure_counts[step_id])
        if step_failure_counts
        else None
    )

    diagnosis_classification_counts: dict[str, int] = {}
    for record in executions:
        if record.diagnosis_classification is not None:
            diagnosis_classification_counts[record.diagnosis_classification] = (
                diagnosis_classification_counts.get(record.diagnosis_classification, 0) + 1
            )

    healing_succeeded_count = sum(1 for e in executions if e.healing_status == HEALING_HEALED)
    healing_failed_count = sum(1 for e in executions if e.healing_status == HEALING_FAILED)
    healing_attempted_count = healing_succeeded_count + healing_failed_count

    evidence: list[str] = [
        f"{executions_analyzed} execution(s) analyzed: {passed_count} passed, {failed_count} failed.",
    ]
    if insufficient_data:
        evidence.append(
            f"Fewer than {MIN_EXECUTIONS_FOR_ANALYSIS} executions are available; "
            "flakiness cannot be determined yet."
        )
    if consistently_failing:
        evidence.append("Every analyzed execution failed; this is a consistent failure, not flakiness.")
    for signature in recurring_signatures:
        evidence.append(
            f"Failure signature (step='{signature.failed_step_id}', "
            f"classification={signature.classification!r}) recurred "
            f"{signature.occurrence_count} time(s) between "
            f"'{signature.first_execution_id}' and '{signature.last_execution_id}'."
        )
    if healing_attempted_count > 0:
        evidence.append(
            f"Healing was attempted {healing_attempted_count} time(s); "
            f"succeeded {healing_succeeded_count} time(s), "
            f"failed {healing_failed_count} time(s)."
        )

    return FlakyAnalysisResult(
        test_definition_id=test_definition_id,
        executions_analyzed=executions_analyzed,
        window_description=window_description,
        insufficient_data=insufficient_data,
        passed_count=passed_count,
        failed_count=failed_count,
        is_flaky=is_flaky,
        flaky_reason=flaky_reason,
        consistently_failing=consistently_failing,
        recurring_signatures=recurring_signatures,
        most_frequent_failing_step_id=most_frequent_failing_step_id,
        diagnosis_classification_counts=diagnosis_classification_counts,
        healing_attempted_count=healing_attempted_count,
        healing_succeeded_count=healing_succeeded_count,
        healing_failed_count=healing_failed_count,
        evidence=evidence,
    )
