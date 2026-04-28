"""Upload Namo Core secrets to GCP Secret Manager.

Values are read from environment variables (or .env file).
Never hardcode secrets in this file.
"""
import os, sys
from pathlib import Path

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # dotenv optional; rely on shell env

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    r"C:\Users\icezi\.gcp\namo-sa-key.json",
)

try:
    from google.cloud import secretmanager
    from google.api_core.exceptions import AlreadyExists
except ImportError:
    print("ERROR: google-cloud-secret-manager not installed.")
    sys.exit(1)

def _require(var: str) -> str:
    value = os.getenv(var)
    if not value:
        print(f"ERROR: environment variable '{var}' is not set.")
        sys.exit(1)
    return value

SECRETS = {
    "namo-reasoning-api-key": _require("GROQ_API_KEY"),
    "namo-groq-api-key":      _require("GROQ_API_KEY"),
    "namo-system-secret":     _require("NAMO_SYSTEM_SECRET"),
    "namo-jwt-secret-key":    _require("NAMO_JWT_SECRET_KEY"),
    "namo-admin-password":    _require("NAMO_ADMIN_PASSWORD"),
    "namo-db-password":       os.getenv("NAMO_DB_PASSWORD", "placeholder-for-cloud-sql"),
    "namo-tts-api-key":       os.getenv("NAMO_TTS_API_KEY", "not-required-edge-tts"),
}

PROJECT = "namo-classroom"
PARENT = f"projects/{PROJECT}"
client = secretmanager.SecretManagerServiceClient()

print(f"Uploading {len(SECRETS)} secrets to GCP project: {PROJECT}\n")

for secret_id, value in SECRETS.items():
    secret_path = f"{PARENT}/secrets/{secret_id}"
    try:
        client.create_secret(request={
            "parent": PARENT,
            "secret_id": secret_id,
            "secret": {"replication": {"automatic": {}}},
        })
        status = "CREATED"
    except AlreadyExists:
        status = "EXISTS "
    except Exception as exc:
        print(f"  [ERROR ] {secret_id}: {exc}")
        continue

    try:
        client.add_secret_version(request={
            "parent": secret_path,
            "payload": {"data": value.encode("utf-8")},
        })
        print(f"  [{status}] {secret_id}: version uploaded")
    except Exception as exc:
        print(f"  [WARN  ] {secret_id} version: {exc}")

print("\nDone.")
