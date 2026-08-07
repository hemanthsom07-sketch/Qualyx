"""
Application configuration.

All configuration is read from environment variables (optionally loaded
from a local .env file). No secrets are hard-coded here.

This module is intentionally minimal for the current milestone: it only
covers what the Project persistence foundation needs. Additional settings
(execution engine config, evidence storage paths, etc.) will be added in
later milestones once the relevant shared contracts are materialized.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"

    # PostgreSQL connection string. Must be provided via environment/.env.
    # No default credentials are baked in here on purpose.
    database_url: str = "postgresql+psycopg2://qualyx_user:qualyx_password@localhost:5432/qualyx"

    # Local-dev convenience flag only. Should be replaced by Alembic
    # migrations before this becomes a real multi-developer concern.
    db_auto_create: bool = True

    # --- Execution Engine boundary (Task 6) ---
    # Path to the execution-engine directory. If unset, it's derived from
    # the repository layout, assuming backend/ and execution-engine/ are
    # sibling directories under the repo root (see services/execution_client.py).
    execution_engine_dir: str | None = None

    # Command used to invoke the execution engine's stdin/stdout entry
    # point. Defaults to `npx tsx`, matching the engine's existing tsx-based
    # scripts (package.json). Overridable for environments that prefer a
    # compiled `node dist/stdin-runner.js` instead.
    execution_engine_command: list[str] = ["npx", "tsx"]

    # Overall subprocess timeout (seconds). This bounds the whole run
    # (all steps), separate from the execution engine's own 5s-per-step
    # internal timeout.
    execution_engine_timeout_seconds: int = 30


settings = Settings()
