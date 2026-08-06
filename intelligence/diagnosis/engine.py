"""
Deterministic Diagnosis Prototype
==================================

Milestone scope (Task 3): the smallest useful, deterministic,
rule-based diagnosis capability. No LLM calls. No healing.
No selector-candidate ranking beyond a simple existence check
used purely to distinguish BROKEN_TEST from other categories.

This module accepts LOCAL prototype fixtures (see local_fixtures.py)
and returns a LOCAL prototype diagnosis result. Field names deliberately
mirror the conceptually-agreed FailureDiagnosis contract (category,
confidence, evidence, explanation) but this is NOT the frozen shared
schema — that will be implemented once /shared/contracts is finalized.

Diagnosis principles enforced here (per Master Prompt Section 5/9):
- Diagnosis happens before any healing consideration.
- No fabricated evidence: every evidence string is derived directly
  from fields present on the input fixtures.
- When signals are insufficient or conflicting, the result is UNCERTAIN
  rather than a forced guess.
"""

from dataclasses import dataclass, field
from typing import Optional

from .local_fixtures import LocalRecordedJourney, LocalExecutionFailure, LocalElementInfo

# Canonical failure categories (per Task 2, Section 4 — names only,
# not the shared enum implementation itself).
APPLICATION_BUG = "APPLICATION_BUG"
BROKEN_TEST = "BROKEN_TEST"
ENVIRONMENT_OR_EXECUTION = "ENVIRONMENT_OR_EXECUTION"
UNCERTAIN = "UNCERTAIN"

_VALID_CATEGORIES = {APPLICATION_BUG, BROKEN_TEST, ENVIRONMENT_OR_EXECUTION, UNCERTAIN}


@dataclass
class LocalDiagnosisResult:
    """LOCAL PROTOTYPE ONLY — not the frozen shared FailureDiagnosis schema."""
    run_id: str
    category: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    explanation: str = ""
    healing_should_be_considered: bool = False

    def __post_init__(self) -> None:
        if self.category not in _VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {self.category}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence out of range: {self.confidence}")


def _find_similar_element(
    missing_selector_step_element: Optional[LocalElementInfo],
    current_dom_elements: list[LocalElementInfo],
) -> Optional[LocalElementInfo]:
    """
    Very small deterministic similarity check: same tag+role and
    overlapping/matching text. This is NOT the future full selector
    candidate-ranking system (explicitly out of scope for this milestone)
    — it exists only to let the prototype distinguish "selector broke but
    an equivalent element still exists" from other failure shapes.
    """
    if missing_selector_step_element is None:
        return None

    for candidate in current_dom_elements:
        same_tag = (
            missing_selector_step_element.tag is not None
            and candidate.tag == missing_selector_step_element.tag
        )
        same_role = (
            missing_selector_step_element.role is not None
            and candidate.role == missing_selector_step_element.role
        )
        text_overlaps = (
            missing_selector_step_element.text is not None
            and candidate.text is not None
            and missing_selector_step_element.text.strip().lower()
            in candidate.text.strip().lower()
        )
        if same_tag and same_role and text_overlaps:
            return candidate

    return None


def diagnose(
    journey: LocalRecordedJourney,
    failure: LocalExecutionFailure,
) -> LocalDiagnosisResult:
    """
    Deterministic, rule-based diagnosis. No AI/LLM involved.

    Rule order (evaluated top to bottom, first confident match wins):

    1. HTTP 5xx / backend error signals -> APPLICATION_BUG (high confidence)
    2. Selector-not-found AND an equivalent element still exists on the
       page -> BROKEN_TEST (medium-high confidence)
    3. Selector-not-found AND no equivalent element found -> UNCERTAIN
       (low confidence) — could be a genuine app change or a broken test;
       insufficient evidence to decide deterministically.
    4. Timeout / network-type errors with no application error signal
       -> ENVIRONMENT_OR_EXECUTION (medium confidence)
    5. Anything else -> UNCERTAIN (low confidence)
    """
    evidence: list[str] = []

    # Locate the step that failed, if we can find it in the journey.
    failed_step = next(
        (s for s in journey.steps if s.step_id == failure.failed_step_id), None
    )
    step_element = failed_step.element if failed_step else None

    # Rule 1: application-side HTTP failure.
    if failure.error_type == "HTTP_ERROR" and failure.http_status is not None:
        if 500 <= failure.http_status < 600:
            evidence.append(
                f"Execution reported HTTP {failure.http_status} during step "
                f"'{failure.failed_step_id}', consistent with a server-side error."
            )
            if failure.error_message:
                evidence.append(f"Reported error message: {failure.error_message}")
            return LocalDiagnosisResult(
                run_id=failure.run_id,
                category=APPLICATION_BUG,
                confidence=0.9,
                evidence=evidence,
                explanation=(
                    "The target application returned a server error "
                    f"(HTTP {failure.http_status}) while executing the expected "
                    "step. This is more consistent with a genuine application "
                    "failure than an outdated test, so healing should not be "
                    "considered."
                ),
                healing_should_be_considered=False,
            )

    # Rule 2 / 3: selector not found.
    if failure.error_type == "SELECTOR_NOT_FOUND":
        evidence.append(
            f"Step '{failure.failed_step_id}' failed because the selector "
            f"'{failure.attempted_selector}' could not be located on the page."
        )
        similar = _find_similar_element(step_element, journey.current_dom_elements)
        if similar is not None:
            evidence.append(
                "An element with matching tag, role, and overlapping text was "
                f"found currently on the page: selector '{similar.selector}'."
            )
            return LocalDiagnosisResult(
                run_id=failure.run_id,
                category=BROKEN_TEST,
                confidence=0.75,
                evidence=evidence,
                explanation=(
                    "The originally recorded selector no longer matches any "
                    "element, but an element with the same role and equivalent "
                    "text still exists on the page. This suggests the "
                    "application's behavior is unchanged and only the "
                    "selector became outdated."
                ),
                healing_should_be_considered=True,
            )
        else:
            evidence.append(
                "No element with matching tag, role, and overlapping text was "
                "found on the current page."
            )
            return LocalDiagnosisResult(
                run_id=failure.run_id,
                category=UNCERTAIN,
                confidence=0.3,
                evidence=evidence,
                explanation=(
                    "The originally recorded selector no longer matches any "
                    "element, and no clearly equivalent element could be found. "
                    "This could indicate either a genuine application change "
                    "(the element was removed or altered) or an outdated test "
                    "with a mismatch too large for this deterministic check to "
                    "resolve. Insufficient evidence to classify confidently."
                ),
                healing_should_be_considered=False,
            )

    # Rule 4: environment/execution-type errors.
    if failure.error_type in {"TIMEOUT", "NETWORK_ERROR", "CONNECTION_RESET"}:
        evidence.append(
            f"Step '{failure.failed_step_id}' failed with error type "
            f"'{failure.error_type}', with no application-level error signal."
        )
        return LocalDiagnosisResult(
            run_id=failure.run_id,
            category=ENVIRONMENT_OR_EXECUTION,
            confidence=0.6,
            evidence=evidence,
            explanation=(
                "The failure signature matches a timeout/network-type issue "
                "rather than an application or selector problem. This is more "
                "consistent with an environment or execution issue."
            ),
            healing_should_be_considered=False,
        )

    # Rule 5: fallback.
    evidence.append(
        f"Error type '{failure.error_type}' did not match any known "
        "deterministic pattern."
    )
    return LocalDiagnosisResult(
        run_id=failure.run_id,
        category=UNCERTAIN,
        confidence=0.2,
        evidence=evidence,
        explanation=(
            "The available evidence does not clearly match a known failure "
            "pattern. Classifying as uncertain rather than guessing."
        ),
        healing_should_be_considered=False,
    )
