"""
Explainability Foundation
==========================

The smallest useful deterministic explainability layer. Consumes the
REAL diagnosis output (diagnosis.failure_diagnosis.FailureDiagnosisResult,
Task 10) and produces a Dashboard-ready, structured explanation.

Scope discipline (per Master Prompt boundary rules):
- This module performs NO classification and NO diagnosis of its own.
  It does not re-derive category, re-inspect the error string, or
  apply any pattern matching against evidence text. classification
  and confidence are copied through from the input verbatim.
- confidence_level is derived ONLY by thresholding the existing
  confidence float -- it adds no new judgment about the failure.
- headline is a short deterministic template keyed only on
  (has_failure, classification) -- never on re-parsing evidence/error
  text.
- No LLM calls, no network calls, no DOM inspection, no healing
  suggestions. Purely presentational: same input always produces the
  same output.

This is explicitly NOT the final shared Explainability contract --
consistent with how every other Intelligence module in this repo is
scoped (LOCAL prototype, not a frozen cross-module schema).
"""

from dataclasses import dataclass, field
from typing import Optional

from ..diagnosis.engine import APPLICATION_BUG, BROKEN_TEST, ENVIRONMENT_OR_EXECUTION, UNCERTAIN
from ..diagnosis.failure_diagnosis import FailureDiagnosisResult

# Confidence-level bands. Derived purely from the numeric confidence
# already produced by diagnosis -- these thresholds do not encode any
# new opinion about which classification is "more true"; they only
# describe how strongly the diagnosis layer itself already believes
# its own result.
CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MODERATE = "MODERATE"
CONFIDENCE_LOW = "LOW"

_VALID_CONFIDENCE_LEVELS = {CONFIDENCE_HIGH, CONFIDENCE_MODERATE, CONFIDENCE_LOW}

# Thresholds chosen to align with the confidence values diagnosis
# actually produces today (see diagnosis/engine.py and
# diagnosis/failure_diagnosis.py): 0.7/0.75/0.9/1.0 -> HIGH,
# 0.55/0.6 -> MODERATE, 0.1-0.3 -> LOW.
_HIGH_THRESHOLD = 0.7
_MODERATE_THRESHOLD = 0.4

_HEADLINES = {
    APPLICATION_BUG: "Likely an application bug",
    BROKEN_TEST: "Likely an outdated/broken test",
    ENVIRONMENT_OR_EXECUTION: "Likely an environment or execution issue",
    UNCERTAIN: "Cause is uncertain",
}

_NO_FAILURE_HEADLINE = "Execution passed"


@dataclass
class ExplainedDiagnosis:
    """
    Structured, Dashboard-ready explanation of a single diagnosis
    result. Every field here is either copied verbatim from the input
    FailureDiagnosisResult, or mechanically derived from it (never
    fabricated, never re-classified).
    """
    has_failure: bool
    classification: Optional[str]  # copied verbatim from diagnosis; None if has_failure is False
    confidence: float  # copied verbatim from diagnosis
    confidence_level: str  # derived only by thresholding `confidence`
    headline: str
    explanation: str  # copied verbatim from diagnosis
    evidence: list[str] = field(default_factory=list)  # copied verbatim from diagnosis

    def __post_init__(self) -> None:
        if self.confidence_level not in _VALID_CONFIDENCE_LEVELS:
            raise ValueError(f"Invalid confidence_level: {self.confidence_level}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence out of range: {self.confidence}")
        if self.has_failure and self.classification is None:
            raise ValueError("classification must be set when has_failure is True")
        if not self.has_failure and self.classification is not None:
            raise ValueError("classification must be None when has_failure is False")


def _confidence_level(confidence: float) -> str:
    """
    Pure threshold on the existing confidence value. Adds no new
    signal -- just names the band the diagnosis layer's own number
    already falls into.
    """
    if confidence >= _HIGH_THRESHOLD:
        return CONFIDENCE_HIGH
    if confidence >= _MODERATE_THRESHOLD:
        return CONFIDENCE_MODERATE
    return CONFIDENCE_LOW


def _headline(has_failure: bool, classification: Optional[str]) -> str:
    """
    Deterministic headline lookup keyed only on
    (has_failure, classification). Never re-parses evidence or error
    text -- if a classification is ever added upstream that this map
    doesn't know about, we fail loudly rather than inventing wording.
    """
    if not has_failure:
        return _NO_FAILURE_HEADLINE

    try:
        return _HEADLINES[classification]
    except KeyError as exc:
        raise ValueError(
            f"No headline template for classification: {classification!r}. "
            "Explainability must not guess wording for a classification "
            "it doesn't recognize."
        ) from exc


def explain_diagnosis(diagnosis: FailureDiagnosisResult) -> ExplainedDiagnosis:
    """
    Turns a real FailureDiagnosisResult into a structured,
    Dashboard-ready explanation.

    Does not duplicate or alter diagnosis/classification logic:
    classification, confidence, explanation, and evidence are all
    taken directly from `diagnosis`. Only confidence_level and
    headline are computed here, and both are purely mechanical
    derivations (a threshold and a lookup table) with no independent
    judgment about the failure itself.
    """
    return ExplainedDiagnosis(
        has_failure=diagnosis.has_failure,
        classification=diagnosis.classification,
        confidence=diagnosis.confidence,
        confidence_level=_confidence_level(diagnosis.confidence),
        headline=_headline(diagnosis.has_failure, diagnosis.classification),
        explanation=diagnosis.explanation,
        evidence=list(diagnosis.evidence),
    )
