"""
Execution Result Contract Mirror (Task 10, updated for confirmed
Backend ExecutionResultOut / FailureEvidenceOut contract)
============================================================================

Mirrors Claude 2's REAL, confirmed ExecutionResultOut contract:

    ExecutionResultOut:
      - status
      - steps
      - failedStepIndex
      - failedStepId
      - error
      - executedStepCount
      - startedAt
      - finishedAt
      - durationMs
      - evidence: FailureEvidenceOut | None

    FailureEvidenceOut:
      - failedStepId
      - failedStepIndex
      - stepType
      - action
      - errorMessage
      - errorCategory
      - pageUrl
      - httpStatus
      - executedStepCount
      - stepDurationMs

This is a read-only Python-side view of that contract for Intelligence
to consume -- it does not redefine or change Claude 2's contract. If a
change to that contract is ever needed, it must be reported, not made
here (per ownership rules).

Only failedStepId (top-level) is treated as the canonical correlation
key for finding the failed generated step. failedStepIndex is carried
through as supplementary evidence only -- it must never become the
mechanism used to look up a generated step. (FailureEvidenceOut also
carries its own failedStepId/failedStepIndex, which are treated the
same way: informative passthrough only, not used for correlation.)

errorCategory (and the rest of FailureEvidenceOut's fields, e.g.
httpStatus, stepType, action, pageUrl, stepDurationMs): Claude 2
confirmed these fields exist and are populated inside `evidence`, but
their exact enum of possible values and semantics have not been shared
with Intelligence. They are therefore modeled here as opaque, optional
passthrough values only. Diagnosis surfaces errorCategory as
supplementary evidence (verbatim) but does NOT use it to drive
classification decisions -- doing so would mean guessing at an
undocumented value space, which risks silently misclassifying
failures. See failure_diagnosis.py's module docstring for the
follow-up needed from Claude 2 before errorCategory can be used as a
primary signal.

Each entry in `steps` is treated as an opaque per-step result (its
exact shape beyond "preserves id" was not specified for this task), so
StepExecutionResult below is intentionally permissive/optional-only.
"""

from dataclasses import dataclass, field
from typing import Optional

STATUS_PASSED = "passed"
STATUS_FAILED = "failed"


@dataclass
class StepExecutionResult:
    """
    One entry from ExecutionResult.steps. Permissive/optional since the
    exact per-step shape was not fully specified for this task -- only
    fields explicitly confirmed (id is preserved) are relied upon by
    the diagnosis logic; everything else here is best-effort passthrough.
    """
    id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FailureEvidence:
    """
    Mirrors Claude 2's confirmed FailureEvidenceOut contract, field for
    field. All fields are opaque passthrough -- no enum values are
    invented or interpreted here.
    """
    failedStepId: Optional[str] = None
    failedStepIndex: Optional[int] = None
    stepType: Optional[str] = None
    action: Optional[str] = None
    errorMessage: Optional[str] = None
    errorCategory: Optional[str] = None  # opaque passthrough; enum/semantics not yet shared
    pageUrl: Optional[str] = None
    httpStatus: Optional[int] = None
    executedStepCount: Optional[int] = None
    stepDurationMs: Optional[int] = None


@dataclass
class ExecutionResult:
    """Mirrors Claude 2's real ExecutionResultOut contract, field for field."""
    status: str  # STATUS_PASSED / STATUS_FAILED
    failedStepIndex: Optional[int] = None
    failedStepId: Optional[str] = None
    error: Optional[str] = None
    executedStepCount: int = 0
    steps: list[StepExecutionResult] = field(default_factory=list)
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    durationMs: Optional[int] = None
    evidence: Optional[FailureEvidence] = None
