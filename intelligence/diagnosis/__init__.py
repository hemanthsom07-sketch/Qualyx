"""
Diagnosis package.

Contains TWO diagnosis paths:

1. Task 3 prototype (engine.py + local_fixtures.py): a deterministic,
   rule-based diagnosis PROTOTYPE built against synthetic
   LocalRecordedJourney/LocalExecutionFailure fixtures. Kept as-is;
   still exercised by its own tests.

2. Task 10 real-pipeline diagnosis (execution_result.py +
   failure_diagnosis.py): consumes the real LocalGeneratedTest (from
   the Recorder -> journey understanding -> test generation pipeline)
   together with Claude 2's real ExecutionResult contract, and
   correlates failures via the existing stable failedStepId mechanism
   (test_generation.execution_payload.find_generated_step_by_id).

Neither path is the final shared FailureDiagnosis implementation.
"""

from .engine import (
    diagnose,
    LocalDiagnosisResult,
    APPLICATION_BUG,
    BROKEN_TEST,
    ENVIRONMENT_OR_EXECUTION,
    UNCERTAIN,
)
from .local_fixtures import (
    LocalRecordedJourney,
    LocalJourneyStep,
    LocalExecutionFailure,
    LocalElementInfo,
)
from .execution_result import ExecutionResult, StepExecutionResult, STATUS_PASSED, STATUS_FAILED
from .failure_diagnosis import FailureDiagnosisResult, diagnose_execution_result

__all__ = [
    "diagnose",
    "LocalDiagnosisResult",
    "APPLICATION_BUG",
    "BROKEN_TEST",
    "ENVIRONMENT_OR_EXECUTION",
    "UNCERTAIN",
    "LocalRecordedJourney",
    "LocalJourneyStep",
    "LocalExecutionFailure",
    "LocalElementInfo",
    "ExecutionResult",
    "StepExecutionResult",
    "STATUS_PASSED",
    "STATUS_FAILED",
    "FailureDiagnosisResult",
    "diagnose_execution_result",
]
