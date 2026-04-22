# -*- coding: utf-8 -*-
"""
upload_to_gcs.py -- Namo Core FAISS & Knowledge Backup to Google Cloud Storage
============================================================================
Backs up the Tripitaka FAISS index + JSONL knowledge chunks to GCS.
Run this whenever the FAISS index is updated to keep cloud copy in sync.

Usage:
    python scripts/upload_to_gcs.py

Environment (set in .env or shell):
    GOOGLE_APPLICATION_CREDENTIALS = path to service account JSON key
    GCS_BUCKET                     = bucket name (default: namo-classroom-models)
    NAMO_PROJECT_ROOT              = project root (default: auto-detected)
"""

import os, sys, hashlib, time
from pathlib import Path
from datetime import datetime, timezone

# Force UTF-8 output to avoid Windows cp1252 issues
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from google.cloud import storage
    from google.api_core.exceptions import NotFound
except ImportError:
    print("ERROR: google-cloud-storage not installed.")
    print("Run: pip install google-cloud-storage")
    sys.exit(1)

# --- Config ------------------------------------------------------------------
BUCKET_NAME = os.getenv("GCS_BUCKET", "namo-classroom-models")
KEY_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Auto-detect project root (2 levels up from scripts/)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.getenv("NAMO_PROJECT_ROOT", str(SCRIPT_DIR.parent)))
DOWNLOADS_ROOT = (
    Path(os.getenv("USERPROFILE", "")) / "Downloads"
)  # for loose JSONL files

# --- Files to upload ---------------------------------------------------------
# (local_path, gcs_path)
STATIC_FILES = [
    (
        PROJECT_ROOT / "knowledge" / "tripitaka_main" / "tripitaka_v45.index",
        "models/tripitaka_v45.index",
    ),
    (
        PROJECT_ROOT / "knowledge" / "tripitaka_main" / "tripitaka_v45_metadata.json",
        "models/tripitaka_v45_metadata.json",
    ),
    (
        PROJECT_ROOT / "knowledge" / "tripitaka_main" / "master_v45_ready.json",
        "models/master_v45_ready.json",
    ),
]

# JSON knowledge sources
JSON_SOURCES = [
    PROJECT_ROOT / "knowledge" / "tripitaka_main",
    PROJECT_ROOT / "knowledge" / "global_library",
]


# --- Helpers -----------------------------------------------------------------
def md5_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Compute MD5 of local file for integrity check."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while data := f.read(chunk_size):
            h.update(data)
    return h.hexdigest()


def upload_file(bucket, local: Path, remote: str, dry_run: bool = False) -> dict:
    """Upload a single file to GCS with progress logging."""
    size_mb = local.stat().st_size / (1024 * 1024)
    print(
        f"  UP  {local.name:50s}  {size_mb:7.1f} MB  ->  gs://{BUCKET_NAME}/{remote}",
        flush=True,
    )

    if dry_run:
        return {"status": "dry_run", "local": str(local), "remote": remote}

    t0 = time.time()
    blob = bucket.blob(remote)
    blob.upload_from_filename(str(local))

    # Write metadata
    blob.metadata = {
        "source_file": local.name,
        "md5": md5_file(local),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": str(local.stat().st_size),
    }
    blob.patch()

    elapsed = time.time() - t0
    speed = size_mb / elapsed if elapsed > 0 else 0
    print(f"     DONE  ({elapsed:.1f}s, {speed:.1f} MB/s)", flush=True)
    return {"status": "ok", "remote": remote, "size_mb": round(size_mb, 2)}


def ensure_bucket(client) -> object:
    """Create bucket if it doesn't exist."""
    bucket = client.bucket(BUCKET_NAME)
    try:
        bucket.reload()
        print(f"[OK] Bucket gs://{BUCKET_NAME} exists", flush=True)
    except NotFound:
        bucket = client.create_bucket(BUCKET_NAME, location="asia-southeast1")
        print(f"[OK] Bucket gs://{BUCKET_NAME} created (asia-southeast1)", flush=True)
    return bucket


# --- Main --------------------------------------------------------------------
def main(dry_run: bool = "--dry-run" in sys.argv):
    print(f"\n{'=' * 60}", flush=True)
    print(f"  Namo Core GCS Upload", flush=True)
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"  Bucket  : gs://{BUCKET_NAME}", flush=True)
    print(f"  Key     : {KEY_FILE}", flush=True)
    print(f"  Root    : {PROJECT_ROOT}", flush=True)
    print(f"  DryRun  : {dry_run}", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    if not KEY_FILE or not Path(KEY_FILE).exists():
        print(
            f"[ERR] Key file not found. Set GOOGLE_APPLICATION_CREDENTIALS environment variable.",
            flush=True,
        )
        sys.exit(1)

    client = storage.Client.from_service_account_json(KEY_FILE)
    bucket = ensure_bucket(client)
    results = []

    # Upload static model files
    print("\n[1/2] Uploading models (FAISS + metadata)...", flush=True)
    for local, remote in STATIC_FILES:
        if local.exists():
            results.append(upload_file(bucket, local, remote, dry_run))
        else:
            print(f"  SKIP (not found): {local.name}", flush=True)
            print(f"       looked at  : {local}", flush=True)

    # Upload JSON knowledge chunks
    print("\n[2/2] Uploading JSON knowledge chunks...", flush=True)
    json_count = 0
    for src_dir in JSON_SOURCES:
        if not src_dir.exists(): continue
        for json_file in sorted(src_dir.glob("*.json")):
            # ข้ามไฟล์ใหญ่ที่อัปโหลดไปแล้วในขั้นตอนที่ 1
            if json_file.name in ["tripitaka_v45_metadata.json", "master_v45_ready.json"]:
                continue
            results.append(upload_file(bucket, json_file, f"data/{json_file.name}", dry_run))
            json_count += 1
    if json_count == 0:
        print("  No .json files found in search paths", flush=True)

    # Summary
    ok = sum(1 for r in results if r.get("status") in ("ok", "dry_run"))
    total = len(results)
    total_mb = sum(r.get("size_mb", 0) for r in results)
    print(f"\n{'=' * 60}", flush=True)
    print(
        f"  Upload complete: {ok}/{total} files ({total_mb:.1f} MB total)", flush=True
    )
    print(
        f"  Browse: https://console.cloud.google.com/storage/browser/{BUCKET_NAME}",
        flush=True,
    )
    print(f"{'=' * 60}\n", flush=True)


if __name__ == "__main__":
    main()
