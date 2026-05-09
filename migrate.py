"""Run alembic upgrade head via Cloud SQL Python Connector (no proxy binary needed)."""

import os, sys

# Add backend to path so namo_core is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "backend", "namo_core"))

# Point to GCP credentials
os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    r"C:\Users\icezi\.gcp\namo-sa-key.json",
)

import sqlalchemy
from google.cloud.sql.connector import Connector
from alembic.config import Config
from alembic import command
from namo_core.config.settings import get_settings

settings = get_settings()

INSTANCE = "namo-classroom:asia-southeast1:namo-classroom-db"
DB_USER = settings.database_user
DB_PASS = settings.database_password or os.environ.get("NAMO_DATABASE_PASSWORD", "")
DB_NAME = "namo_classroom"

connector = Connector()


def getconn():
    return connector.connect(
        INSTANCE, "pg8000", user=DB_USER, password=DB_PASS, db=DB_NAME
    )


engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)

print("Connecting to Cloud SQL...")
with engine.connect() as conn:
    print("Connected OK — running alembic upgrade head...")
    alembic_cfg = Config("alembic.ini")
    # Pass live connection so alembic skips its own URL lookup
    alembic_cfg.attributes["connection"] = conn
    command.upgrade(alembic_cfg, "head")

connector.close()
print("=== Migration complete! ===")
