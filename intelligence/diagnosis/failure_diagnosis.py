"""
Failure Diagnosis Foundation (Task 10)
==========================================

The first diagnosis layer that consumes the REAL pipeline output
(LocalGeneratedTest, from Task 4/5/7/9) together with Claude 2's REAL
ExecutionResult contract (Task 8/10), rather than the Task 3 synthetic
LocalRecordedJourney/LocalExecutionFailure fixtures.

This module does not replace or modify Task 3's diagnosis/engine.py
prototype -- that remains as-is and its tests remain green. This is an
additive, separate diagnosis path built for the real pipeline.

Correlation rule (per Task 10 contract):
    - failedStepId is the ONLY canonical correlation key. It is looked
      up via test_generation.execution_payload.find_generated_step_by_id
      (existing, unmodified Task 8 function) -- never reimplemented.
    - failedStepIndex is carried through as supplementary evidence
      only. It is never used to look up a generated step.
    - If failedStepId is None, or does not match any generated step,
      correlation has failed. The diagnosis is forced to UNCERTAIN in
      that case (see requirement E) -- no step id is ever fabricated,
      and no other classification rule is allowed to override this.

Classification rules (deterministic, string-pattern based on the
single `error` string Claude 2's real contract provides -- there is no
structured error_type/http_status field in this contract, unlike the
Task 3 prototype's richer synthetic fixture):
    1. status == "passed"            -> no failure to diagnose.
    2. status == "failed" and
       correlation could not be
       established                    -> UNCERTAIN (forced, per requirement E).
    3. status == "failed", correlated, error text matches an
       HTTP 5xx pattern (e.g. contains "500", "502", "503", "504")
                                       -> APPLICATION_BUG, moderate confidence.
    4. status == "failed", correlated, error text matches
       timeout/network/connection keywords
                                       -> ENVIRONMENT_OR_EXECUTION, moderate confidence.
    5. status == "failed", correlated, error text mentions
       selector/locator/"not found"   -> UNCERTAIN. A generic string
       alone cannot distinguish "selector genuinely outdated" from
       "element genuinely removed by an application change" without
       DOM evidence, which this contract does not provide. Evidence
       still notes the generated step's attempted selector, for
       context, but confidence stays low and no BROKEN_TEST or
       APPLICATION_BUG claim is made from that alone.
    6. Anything else                 -> UNCERTAIN, low confidence.

This is intentionally conservative: a single free-text error string is
not sufficient to reliably claim an application bug, so classification
never asserts confidence higher than what a plain, explainable string
match justifies.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from .engine import APPLICATION_BUG, BROKEN_TEST, ENVIRONMENT_OR_EXECUTION, UNCERTAIN
from .execution_result import ExecutionResult, STATUS_PASSED, STATUS_FAILED
from ..test_generation.generated_test import LocalGeneratedTest
from ..test_generation.execution_payload import find_generated_step_by_id

_VALID_CATEGORIES = {APPLICATION_BUG, BROKEN_TEST, ENVIRONMENT_OR_EXECUTION, UNCERTAIN}

_HTTP_5XX_PATTERN = re.compile(r"\b5\d{2}\b")
_ENVIRONMENT_KEYWORDS = ("timeout", "timed out", "network", "connection reset", "econnreset")
_SELECTOR_KEYWORDS = ("selector", "locator", "not found", "no element", "no node found")


@dataclass
class FailureDiagnosisResult:
    """
    Typed diagnosis result for the real execution pipeline. Contains
    enough information for downstream Dashboard/backend integration
    without over-engineering: classification, confidence, evidence,
    an explanation, and full provenance for the correlated step
    (when correlation succeeded).
    """
    has_failure: bool
    classification: Optional[str] = None  # one of _VALID_CATEGORIES, or None if has_failure=False
    confidence: float = 0.0
    correlation_established: bool = False

    # Verbatim from ExecutionResult -- never fabricated.
    failed_step_id: Optional[str] = None
    failed_step_index: Optional[int] = None
    error: Optional[str] = None

    # Provenance of the correlated generated step, when found.
    generated_step_id: Optional[str] = None
    source_step_id: Optional[str] = None
    source_event_id: Optional[str] = None

    evidence: list[str] = field(default_factory=list)
    explanation: str = ""

    def __post_init__(self) -> None:
        if self.has_failure:
            if self.classification not in _VALID_CATEGORIES:
                raise ValueError(f"Invalid classification: {self.classification}")
        else:
            if self.classification is not None:
                raise ValueError("classification must be None when has_failure is False")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence out of range: {self.confidence}")


def _no_failure_result() -> FailureDiagnosisResult:
    return FailureDiagnosisResult(
        has_failure=False,
        classification=None,
        confidence=1.0,
        correlation_established=False,
        evidence=["Execution status was 'passed'; there is no failure to diagnose."],
        explanation="Execution completed successfully. No diagnosis is necessary.",
    )


def _uncertain_uncorrelated_result(execution_result: ExecutionResult) -> FailureDiagnosisResult:
    evidence = [
        "Execution status was 'failed', but the failed step could not be "
        "correlated to a generated step."
    ]
    if execution_result.failedStepId is None:
        evidence.append("ExecutionResult.failedStepId was null.")
    else:
        evidence.append(
            f"ExecutionResult.failedStepId ('{execution_result.failedStepId}') did not "
            "match any known generated step id."
        )
    if execution_result.failedStepIndex is not None:
        evidence.append(
            f"ExecutionResult.failedStepIndex was {execution_result.failedStepIndex}, "
            "but array position is not used as a substitute correlation key."
        )
    if execution_result.error:
        evidence.append(f"Reported error: {execution_result.error}")

    return FailureDiagnosisResult(
        has_failure=True,
        classification=UNCERTAIN,
        confidence=0.1,
        correlation_established=False,
        failed_step_id=execution_result.failedStepId,
        failed_step_index=execution_result.failedStepIndex,
        error=execution_result.error,
        evidence=evidence,
        explanation=(
            "The execution reported a failure, but Intelligence could not "
            "correlate it to a specific generated step because no matching "
            "stable step id was available. No step id was fabricated, and "
            "the reported array index was not used as a substitute "
            "correlation key. Classifying as uncertain until a valid "
            "failedStepId is available."
        ),
    )


def diagnose_execution_result(
    generated_test: LocalGeneratedTest,
    execution_result: ExecutionResult,
) -> FailureDiagnosisResult:
    """
    Deterministic diagnosis entry point for the real pipeline. No LLM,
    no network calls, no timestamps or randomness used in the
    classification decision -- the same generated_test + execution_result
    always produces the same result.
    """
    if execution_result.status == STATUS_PASSED:
        return _no_failure_result()

    if execution_result.status != STATUS_FAILED:
        # Defensive: an unrecognized status string is itself evidence
        # of an execution/environment problem, not something to guess
        # a bug/broken-test classification from.
        return FailureDiagnosisResult(
            has_failure=True,
            classification=UNCERTAIN,
            confidence=0.1,
            correlation_established=False,
            failed_step_id=execution_result.failedStepId,
            failed_step_index=execution_result.failedStepIndex,
            error=execution_result.error,
            evidence=[f"Unrecognized execution status: '{execution_result.status}'."],
            explanation=(
                "The execution result reported a status this diagnosis layer "
                "does not recognize. Classifying as uncertain rather than "
                "guessing."
            ),
        )

    # status == "failed" from here on.
    matched_step = find_generated_step_by_id(generated_test, execution_result.failedStepId)

    if matched_step is None:
        return _uncertain_uncorrelated_result(execution_result)

    # Correlation succeeded -- build provenance-rich, string-pattern-based evidence.
    evidence: list[str] = [
        f"Execution failed at step '{matched_step.step_id}' "
        f"(type: {matched_step.kind}), correlated via failedStepId."
    ]
    if execution_result.failedStepIndex is not None:
        evidence.append(
            f"ExecutionResult.failedStepIndex was {execution_result.failedStepIndex} "
            "(supplementary only; not used for correlation)."
        )
    if matched_step.selector:
        evidence.append(f"The step's generated selector was: {matched_step.selector}")
    if matched_step.url:
        evidence.append(f"The step's target URL was: {matched_step.url}")

    error_text = execution_result.error or ""
    error_lower = error_text.lower()

    if execution_result.error:
        evidence.append(f"Reported error: {execution_result.error}")

    common_kwargs = dict(
        has_failure=True,
        correlation_established=True,
        failed_step_id=execution_result.failedStepId,
        failed_step_index=execution_result.failedStepIndex,
        error=execution_result.error,
        generated_step_id=matched_step.step_id,
        source_step_id=matched_step.source_step_id,
        source_event_id=matched_step.source_event_id,
    )

    if _HTTP_5XX_PATTERN.search(error_text):
        evidence.append(
            "The error text contains a pattern consistent with an HTTP "
            "server error (5xx)."
        )
        return FailureDiagnosisResult(
            **common_kwargs,
            classification=APPLICATION_BUG,
            confidence=0.7,
            evidence=evidence,
            explanation=(
                "The reported error text matches a server-error (5xx) "
                "pattern. This is more consistent with a genuine "
                "application failure than an outdated test. Confidence is "
                "moderate rather than high because this contract only "
                "provides a free-text error string, not a structured HTTP "
                "status field."
            ),
        )

    if any(keyword in error_lower for keyword in _ENVIRONMENT_KEYWORDS):
        evidence.append(
            "The error text matches timeout/network/connection-related "
            "keywords, with no application-level error signal."
        )
        return FailureDiagnosisResult(
            **common_kwargs,
            classification=ENVIRONMENT_OR_EXECUTION,
            confidence=0.55,
            evidence=evidence,
            explanation=(
                "The failure text matches a timeout/network-type pattern "
                "rather than an application or selector problem, so this "
                "is classified as an environment/execution issue."
            ),
        )

    if any(keyword in error_lower for keyword in _SELECTOR_KEYWORDS):
        evidence.append(
            "The error text references a selector/locator/'not found' "
            "condition. Without DOM evidence, this cannot be reliably "
            "distinguished between a genuinely outdated test selector and "
            "a genuine application change that removed the element."
        )
        return FailureDiagnosisResult(
            **common_kwargs,
            classification=UNCERTAIN,
            confidence=0.25,
            evidence=evidence,
            explanation=(
                "The failure appears selector/locator-related, but this "
                "diagnosis layer only has a free-text error string and no "
                "current-DOM evidence to compare against. Classifying as "
                "uncertain rather than guessing whether this is a broken "
                "test or a genuine application change."
            ),
        )

    evidence.append(
        "The error text did not match any known deterministic pattern."
    )
    return FailureDiagnosisResult(
        **common_kwargs,
        classification=UNCERTAIN,
        confidence=0.15,
        evidence=evidence,
        explanation=(
            "The available evidence does not clearly match a known failure "
            "pattern. A single free-text error string is not sufficient to "
            "reliably classify this failure, so it is marked uncertain "
            "rather than guessed."
        ),
    )
