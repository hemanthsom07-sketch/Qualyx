"""
Explainability package.

Smallest useful deterministic explainability layer (see engine.py).
Consumes the real diagnosis.failure_diagnosis.FailureDiagnosisResult
and produces a structured, Dashboard-ready explanation. Purely
presentational: no new classification logic, no LLM, no network
calls, no DOM inspection, no healing suggestions.

This is NOT the final shared Explainability contract -- consistent
with every other Intelligence module in this repo being a LOCAL
prototype pending /shared/contracts finalization.
"""

from .engine import (
    explain_diagnosis,
    ExplainedDiagnosis,
    CONFIDENCE_HIGH,
    CONFIDENCE_MODERATE,
    CONFIDENCE_LOW,
)

__all__ = [
    "explain_diagnosis",
    "ExplainedDiagnosis",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_MODERATE",
    "CONFIDENCE_LOW",
]
