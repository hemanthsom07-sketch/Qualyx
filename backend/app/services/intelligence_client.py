"""
Backend <-> Intelligence boundary.

Unlike the Backend <-> Execution Engine boundary (a cross-language
subprocess/JSON boundary, since the Execution Engine is TypeScript),
Backend and Intelligence are both plain Python packages living as
siblings under the repository root. There is no installable packaging
connecting them (no pyproject.toml/setup.py in intelligence/), and
adding one is out of scope here (that would mean modifying Intelligence,
which this task must not do).

Confirmed by inspection (not assumed):
- `backend/` is launched with itself as CWD (`cd backend && uvicorn
  app.main:app`), and `pytest.ini`'s `pythonpath = .` adds that same
  directory for tests. Neither launch path puts the repository root on
  sys.path, so `intelligence/` (a sibling of `backend/`, not a
  subdirectory of it) is not importable without adjustment.
- `intelligence/` is a normal Python package (`intelligence/__init__.py`
  exists) with no build/packaging metadata of its own.

This module makes the narrowest possible adjustment to fix that: it
inserts the repository root into sys.path, guarded against duplicate
insertion, scoped to only this file (not main.py, not global app
startup). The default path is derived the same way `execution_engine_dir`
already derives its sibling-directory default in app/config.py.
"""

import sys
from pathlib import Path

from app.config import settings


def _ensure_intelligence_importable() -> None:
    if settings.intelligence_dir:
        intelligence_dir = Path(settings.intelligence_dir).resolve()
    else:
        # Default: backend/ and intelligence/ are sibling directories
        # under the repository root.
        # this file: backend/app/services/intelligence_client.py
        # parents[0] = services, [1] = app, [2] = backend
        backend_dir = Path(__file__).resolve().parents[2]
        intelligence_dir = (backend_dir.parent / "intelligence").resolve()

    repo_root = str(intelligence_dir.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_intelligence_importable()

# Imported only after the path adjustment above. These are Intelligence's
# existing, unmodified entry points — confirmed field-for-field against
# the actual uploaded source of journey_understanding/recorder_adapter.py
# and pipeline.py; nothing here re-implements or duplicates their logic.
from intelligence.journey_understanding.recorder_adapter import RealRecordedEvent  # noqa: E402
from intelligence.pipeline import generate_execution_payload_from_real_recorder_events  # noqa: E402


class IntelligenceProcessingError(RuntimeError):
    """
    Raised when Intelligence's own pipeline raises while processing a
    recording. Distinct from a request-validation error (422): the
    request was well-formed, but Intelligence itself could not process
    it — analogous to ExecutionEngineError for the Execution Engine
    boundary.
    """


def build_execution_payload_from_events(journey_id: str, events: list[dict]) -> dict:
    """
    Converts already-validated Recorder event dicts (see
    app/schemas/recording.py's RecordedEventCreate — field names mirror
    Recorder's actual RecordedEvent contract exactly) into Intelligence's
    RealRecordedEvent dataclass, then calls the EXISTING, unmodified
    generate_execution_payload_from_real_recorder_events() pipeline
    entry point.

    No Intelligence logic (journey understanding, test generation, step
    ID derivation) is duplicated here — this function only translates
    validated dicts into the dataclass shape Intelligence's own adapter
    expects, and returns exactly what the pipeline gives back:
    {"journeyId": ..., "steps": [...]}.
    """
    real_events = [RealRecordedEvent(**event) for event in events]
    try:
        return generate_execution_payload_from_real_recorder_events(journey_id, real_events)
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any
        # failure inside Intelligence's pipeline should surface as an
        # upstream processing error, not an unhandled 500.
        raise IntelligenceProcessingError(str(exc)) from exc
