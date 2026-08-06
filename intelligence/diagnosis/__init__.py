"""
Diagnosis package — Task 3 milestone.

Contains a deterministic, rule-based diagnosis PROTOTYPE only.
See engine.py for the diagnosis logic and local_fixtures.py for
the temporary local data types used to exercise it.

This is NOT the final shared FailureDiagnosis implementation.
"""

from .engine import diagnose, LocalDiagnosisResult
from .local_fixtures import (
    LocalRecordedJourney,
    LocalJourneyStep,
    LocalExecutionFailure,
    LocalElementInfo,
)

__all__ = [
    "diagnose",
    "LocalDiagnosisResult",
    "LocalRecordedJourney",
    "LocalJourneyStep",
    "LocalExecutionFailure",
    "LocalElementInfo",
]
