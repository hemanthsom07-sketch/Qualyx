"""
Flaky/recurring-failure analysis package (Phase 5, Stage 1).

Pure, deterministic engine consuming historical execution records (see
engine.py's ExecutionRecord) and producing a FlakyAnalysisResult. No
SQLAlchemy, no Backend imports, no LLM, no fabricated confidence
scores. A Backend boundary (a later, not-yet-approved stage) is
responsible for translating real ExecutionRun rows into ExecutionRecord
before calling analyze_executions().
"""

from .engine import (
    analyze_executions,
    ExecutionRecord,
    FlakyAnalysisResult,
    RecurringSignature,
    MIN_EXECUTIONS_FOR_ANALYSIS,
    MIN_OCCURRENCES_TO_RECUR,
)

__all__ = [
    "analyze_executions",
    "ExecutionRecord",
    "FlakyAnalysisResult",
    "RecurringSignature",
    "MIN_EXECUTIONS_FOR_ANALYSIS",
    "MIN_OCCURRENCES_TO_RECUR",
]
