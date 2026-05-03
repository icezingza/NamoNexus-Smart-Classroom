"""GCP Secret Manager utility for Namo Core."""

import logging
import os
from pathlib import Path

from google.cloud import secretmanager
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger(__name__)

_PLACEHOLDER = "MUST_BE_SET_IN_ENV"

# Secrets that are hard-required for the API to function correctly.
_REQUIRED_SECRETS = ("jwt_secret_key", "admin_password", "system_secret")


async def load_secret_from_gcp(secret_name: str, project_id: str) -> str | None:
    """Load one secret from GCP Secret Manager.

    Returns the secret value on success, or None on any failure (never raises).
    Callers decide whether a None result is fatal.
    """
    import asyncio

    def _fetch() -> str:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    try:
        return await asyncio.to_thread(_fetch)
    except GoogleAPIError as exc:
        logger.warning("GCP secret '%s' not found or inaccessible: %s", secret_name, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error loading GCP secret '%s': %s", secret_name, exc)
        return None


async def load_all_secrets() -> None:
    """Load all required secrets from GCP and update settings.

    Strategy:
    - If GOOGLE_APPLICATION_CREDENTIALS is absent → skip entirely (local .env mode).
    - If GCP is reachable → override settings with cloud values.
    - If a secret is missing from GCP → keep the .env value already loaded by Pydantic.
    - After loading, validate that no required setting still holds a placeholder value.
      If a placeholder survives, log a CRITICAL warning (don't crash — the .env fallback
      may be intentionally set for local edge development).
    """
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path)

    from namo_core.config.settings import get_settings

    settings = get_settings()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "namo-classroom")

    logger.info("Loading secrets from GCP Secret Manager (project: %s)...", project_id)

    # --- JWT secret ---
    val = await load_secret_from_gcp("namo-jwt-secret", project_id)
    if val:
        settings.jwt_secret_key = val
        settings.system_secret = val  # keep in sync

    # --- Admin password ---
    val = await load_secret_from_gcp("namo-admin-password", project_id)
    if val:
        settings.admin_password = val

    # --- Groq / reasoning API key ---
    val = await load_secret_from_gcp("namo-groq-api-key", project_id)
    if val:
        settings.reasoning_api_key = val

    # --- Database password (Phase 3 cloud path) ---
    db_pass = await load_secret_from_gcp("namo-database-password", project_id)
    if db_pass:
        settings.database_password = db_pass
        db_host = os.environ.get("NAMO_DB_HOST", "127.0.0.1")
        settings.database_url = (
            f"postgresql://postgres:{db_pass}@{db_host}:5432/namo_classroom"
        )

    # --- Redis password (Phase 3 cloud path) ---
    redis_pass = await load_secret_from_gcp("namo-redis-password", project_id)
    if redis_pass:
        settings.redis_password = redis_pass
        redis_host = os.environ.get("NAMO_REDIS_HOST", "127.0.0.1")
        settings.redis_url = f"redis://:{redis_pass}@{redis_host}:6379/0"

    # --- Post-load validation ---
    _validate_secrets(settings)
    logger.info("GCP secret load complete.")


def _validate_secrets(settings) -> None:
    """Warn loudly if any required secret is still a placeholder after loading."""
    placeholders_found = []

    checks = {
        "jwt_secret_key": settings.jwt_secret_key,
        "system_secret": settings.system_secret,
        "admin_password": settings.admin_password,
    }
    for name, value in checks.items():
        if not value or value == _PLACEHOLDER:
            placeholders_found.append(name)

    if placeholders_found:
        logger.critical(
            "SECURITY WARNING: The following secrets still hold placeholder values "
            "after GCP load attempt: %s. "
            "Set them in .env or ensure GCP Secret Manager contains the correct secrets.",
            placeholders_found,
        )
    else:
        logger.info("Secret validation passed — no placeholder values detected.")
