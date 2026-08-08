"""
Execution Result Contract Mirror (Task 10)
=============================================

Mirrors Claude 2's REAL ExecutionResult contract, as described for
Task 10 (Execution Engine, checkpointed and tested on Claude 2's side):

    {
      status: "passed" | "failed",
      failedStepIndex: number | null,
      failedStepId: string | null,
      error: string | null,
      executedStepCount: number,
      steps: [...],
      startedAt: string,
      finishedAt: string,
      durationMs: number
    }

This is a read-only Python-side view of that contract for Intelligence
to consume -- it does not redefine or change Claude 2's contract. If a
change to that contract is ever needed, it must be reported, not made
here (per ownership rules).

Only failedStepId is treated as the canonical correlation key for
finding the failed generated step. failedStepIndex is carried through
as supplementary evidence only -- it must never become the mechanism
used to look up a generated step.

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
class ExecutionResult:
    """Mirrors Claude 2's real ExecutionResult contract, field for field."""
    status: str  # STATUS_PASSED / STATUS_FAILED
    failedStepIndex: Optional[int] = None
    failedStepId: Optional[str] = None
    error: Optional[str] = None
    executedStepCount: int = 0
    steps: list[StepExecutionResult] = field(default_factory=list)
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    durationMs: Optional[int] = None
