"""GCP Secret Manager utility for Namo Core."""

import logging
import os
from google.cloud import secretmanager
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger(__name__)

async def load_secret_from_gcp(secret_name: str, project_id: str) -> str:
    """Load secret from Google Cloud Secret Manager via client library."""
    try:
        # Import inside to avoid crashing if library is not installed
        import asyncio
        
        def _fetch():
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8").strip()

        return await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.error(f"Failed to load secret {secret_name} from GCP: {e}")
        raise

async def load_all_secrets():
    """Load all required secrets and update settings."""
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path)  # Ensure os.environ is populated from .env file

    from namo_core.config.settings import get_settings
    settings = get_settings()
    
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "namo-classroom")
    
    try:
        logger.info("Loading secrets from GCP Secret Manager...")

        # We can run these concurrently, but sequentially is fine for startup
        settings.jwt_secret_key = (await load_secret_from_gcp("namo-jwt-secret", project_id)).strip()
        settings.admin_password = (await load_secret_from_gcp("namo-admin-password", project_id)).strip()
        settings.reasoning_api_key = (await load_secret_from_gcp("namo-groq-api-key", project_id)).strip()
        # Database and Redis passwords (Phase 3)
        settings.database_password = (await load_secret_from_gcp("namo-database-password", project_id)).strip()
        settings.redis_password = (await load_secret_from_gcp("namo-redis-password", project_id)).strip()

        # Build connection strings if we are in Cloud-Native mode (indicated by having secrets)

        db_host = os.environ.get("NAMO_DB_HOST", "127.0.0.1")
        redis_host = os.environ.get("NAMO_REDIS_HOST", "127.0.0.1")
        
        # Override SQLite with PostgreSQL
        settings.database_url = f"postgresql://postgres:{settings.database_password}@{db_host}:5432/namo_classroom"
        # Set Redis URL
        settings.redis_url = f"redis://:{settings.redis_password}@{redis_host}:6379/0"
        
        # System secret uses JWT secret as a fallback or if we want to sync them
        settings.system_secret = settings.jwt_secret_key
        
        logger.info("Successfully loaded all secrets from GCP Secret Manager.")
    except Exception as e:
        logger.error(f"Critical error loading secrets: {e}")
        # In a real production environment, you might want to raise here
        # raise e
