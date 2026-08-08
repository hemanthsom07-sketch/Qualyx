"""
Backend <-> Execution Engine boundary (Task 6 §E).

The backend does NOT implement browser automation. It never imports
Playwright and contains no navigate/click/fill logic of its own. Instead
it invokes the existing Node/TypeScript Execution Engine (also owned by
Claude 2) as a subprocess, communicating over a small, deterministic
JSON stdin/stdout interface, and maps the engine's ExecutionResult into
a Pydantic model for the API response.

Protocol (matches execution-engine/src/stdin-runner.ts exactly):
  stdin  (JSON): {"steps": [...], "baseUrl"?: str}
  stdout (JSON): either a well-formed ExecutionResult, or
                 {"error": "validation_error" | "invalid_json", "message": str}
  exit codes: 0 = passed, 1 = failed (still a valid ExecutionResult),
              2 = input validation error, 3 = unexpected engine error
"""

import json
import subprocess
from pathlib import Path

from app.config import settings
from app.schemas.execution import ExecutionResultOut


class ExecutionEngineError(RuntimeError):
    """
    Raised when the execution engine subprocess itself could not be
    invoked, timed out, or returned something the backend couldn't
    parse. This is distinct from a normal "failed" execution result,
    which is a well-formed, successful API response.
    """


class ExecutionValidationError(ValueError):
    """
    Raised when the execution engine rejected the step shape itself
    (exit code 2). Distinct from an ExecutionEngineError: this reflects
    bad input, not an engine malfunction.
    """


def _resolve_execution_engine_dir() -> Path:
    if settings.execution_engine_dir:
        return Path(settings.execution_engine_dir).resolve()

    # Default: backend/ and execution-engine/ are sibling directories
    # under the repository root.
    # this file: backend/app/services/execution_client.py
    # parents[0] = services, [1] = app, [2] = backend
    backend_dir = Path(__file__).resolve().parents[2]
    return (backend_dir.parent / "execution-engine").resolve()


def execute_steps(steps: list[dict], base_url: str | None = None) -> ExecutionResultOut:
    """
    Invokes the execution engine's stdin/stdout entry point with the
    given steps and returns the parsed ExecutionResult.

    Raises:
        ExecutionValidationError: the steps were rejected by the
            engine's own validation (bad shape/unknown step type).
        ExecutionEngineError: the subprocess could not be invoked, timed
            out, or returned output the backend could not parse.
    """
    engine_dir = _resolve_execution_engine_dir()
    entry_point = engine_dir / "src" / "stdin-runner.ts"

    if not entry_point.exists():
        raise ExecutionEngineError(f"Execution engine entry point not found at {entry_point}")

    payload: dict = {"steps": steps}
    if base_url:
        payload["baseUrl"] = base_url

    command = [*settings.execution_engine_command, str(entry_point)]

    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(engine_dir),
            timeout=settings.execution_engine_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExecutionEngineError(f"Execution engine timed out after {settings.execution_engine_timeout_seconds}s") from exc
    except OSError as exc:
        raise ExecutionEngineError(f"Failed to invoke execution engine ({command}): {exc}") from exc

    stdout = completed.stdout.strip()

    if completed.returncode == 2:
        try:
            error_payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ExecutionEngineError(
                f"Execution engine reported a validation error but returned invalid JSON: {stdout!r}"
            ) from exc
        raise ExecutionValidationError(error_payload.get("message", "Invalid test steps"))

    if completed.returncode not in (0, 1):
        raise ExecutionEngineError(
            f"Execution engine exited unexpectedly (code {completed.returncode}): "
            f"{completed.stderr.strip() or stdout}"
        )

    try:
        result_json = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ExecutionEngineError(
            f"Execution engine returned invalid JSON: {stdout!r} (stderr: {completed.stderr.strip()!r})"
        ) from exc

    return ExecutionResultOut.model_validate(result_json)
