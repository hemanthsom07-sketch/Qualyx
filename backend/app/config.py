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

    # --- Intelligence boundary ---
    # Path to the intelligence/ directory. If unset, derived from the
    # repository layout (backend/ and intelligence/ are sibling
    # directories under the repo root), mirroring execution_engine_dir's
    # convention above. Unlike the Execution Engine (TypeScript, reached
    # via a subprocess/JSON boundary), Intelligence is also plain Python
    # — but there is no installable package connecting the two (no
    # pyproject.toml/setup.py in intelligence/, and adding one is out of
    # scope: that would mean modifying Intelligence). See
    # app/services/intelligence_client.py for how this path is used to
    # make the `intelligence` package importable from within backend/.
    intelligence_dir: str | None = None

    # --- CORS ---
    # Explicit allow-list of local development origins (Dashboard's Vite
    # dev server, common alternate dev ports), rather than
    # allow_origins=["*"]. This API has no authentication yet, so a
    # wildcard would let any site a user's browser happens to visit call
    # it. Override via CORS_ALLOWED_ORIGINS for other local setups.
    #
    # Note: this does not necessarily cover the Recorder (a Chrome
    # extension) — extension-originated requests may or may not be
    # subject to CORS at all depending on the extension's manifest
    # permissions, which this repo's Backend has no visibility into. See
    # the Day 1 report's "concerns for Recorder integration" section.
    cors_allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
