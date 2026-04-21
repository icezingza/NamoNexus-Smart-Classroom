"""
upload_to_gcs.py — Namo Core FAISS & Knowledge Backup to Google Cloud Storage
============================================================================
Backs up the Tripitaka FAISS index + JSONL knowledge chunks to GCS.
Run this whenever the FAISS index is updated to keep cloud copy in sync.

Usage:
    python scripts/upload_to_gcs.py

Environment (set in .env or shell):
    GOOGLE_APPLICATION_CREDENTIALS = path to service account JSON key
    GCS_BUCKET                     = bucket name (default: namo-classroom)
    NAMO_PROJECT_ROOT              = project root (default: auto-detected)
"""
import os, sys, hashlib, json, time
from pathlib import Path
from datetime import datetime, timezone

try:
    from google.cloud import storage
    from google.api_core.exceptions import NotFound
except ImportError:
    print("ERROR: google-cloud-storage not installed.")
    print("Run: pip install google-cloud-storage")
    sys.exit(1)

# ─── Config ──────────────────────────────────────────────
BUCKET_NAME = os.getenv("GCS_BUCKET", "namo-classroom")
KEY_FILE    = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    r"C:\Users\icezi\namo_core_key.json"   # local path — never commit this file
)

# Auto-detect project root (2 levels up from scripts/)
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.getenv("NAMO_PROJECT_ROOT", SCRIPT_DIR.parent))
DOWNLOADS_ROOT = Path(r"C:\Users\icezi")   # for loose JSONL files

# ─── Files to upload ─────────────────────────────────────
# (local_path, gcs_path)
STATIC_FILES = [
    (PROJECT_ROOT / "backend" / "namo_core" / "knowledge" / "tripitaka" / "tripitaka_index.faiss",
     "models/tripitaka_index.faiss"),
    (PROJECT_ROOT / "backend" / "namo_core" / "knowledge" / "tripitaka" / "tripitaka_metadata.json",
     "models/tripitaka_metadata.json"),
    (PROJECT_ROOT / "backend" / "namo_core" / "knowledge" / "tripitaka" / "ingestion_state.json",
     "models/ingestion_state.json"),
]

# JSONL knowledge chunks (may be in project or Downloads)
JSONL_SOURCES = [
    PROJECT_ROOT / "backend" / "namo_core" / "knowledge" / "tripitaka",
    DOWNLOADS_ROOT,
]

# ─── Helpers ─────────────────────────────────────────────
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
    print(f"  ⬆  {local.name:50s}  {size_mb:7.1f} MB  →  gs://{BUCKET_NAME}/{remote}")

    if dry_run:
        return {"status": "dry_run", "local": str(local), "remote": remote}

    t0 = time.time()
    blob = bucket.blob(remote)
    blob.upload_from_filename(str(local))

    # Write metadata
    blob.metadata = {
        "source_file": local.name,
        "md5":         md5_file(local),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes":  str(local.stat().st_size),
    }
    blob.patch()

    elapsed = time.time() - t0
    speed   = size_mb / elapsed if elapsed > 0 else 0
    print(f"     ✅ Done  ({elapsed:.1f}s, {speed:.1f} MB/s)")
    return {"status": "ok", "remote": remote, "size_mb": round(size_mb, 2)}

def ensure_bucket(client) -> object:
    """Create bucket if it doesn't exist."""
    bucket = client.bucket(BUCKET_NAME)
    try:
        bucket.reload()
        print(f"✅ Bucket gs://{BUCKET_NAME} exists")
    except NotFound:
        bucket = client.create_bucket(BUCKET_NAME, location="asia-southeast1")
        print(f"✅ Bucket gs://{BUCKET_NAME} created (asia-southeast1)")
    return bucket

# ─── Main ────────────────────────────────────────────────
def main(dry_run: bool = "--dry-run" in sys.argv):
    print(f"\n{'='*60}")
    print(f"  Namo Core GCS Upload")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Bucket  : gs://{BUCKET_NAME}")
    print(f"  Key     : {KEY_FILE}")
    print(f"  DryRun  : {dry_run}")
    print(f"{'='*60}\n")

    if not Path(KEY_FILE).exists():
        print(f"❌ Key file not found: {KEY_FILE}")
        print("   Set GOOGLE_APPLICATION_CREDENTIALS env var or place key at default path.")
        sys.exit(1)

    client = storage.Client.from_service_account_json(KEY_FILE)
    bucket = ensure_bucket(client)
    results = []

    # Upload static model files
    print("\n[1/2] Uploading models (FAISS + metadata)...")
    for local, remote in STATIC_FILES:
        if local.exists():
            results.append(upload_file(bucket, local, remote, dry_run))
        else:
            print(f"  ⚠️  SKIP (not found): {local.name}")

    # Upload JSONL knowledge chunks
    print("\n[2/2] Uploading JSONL knowledge chunks...")
    jsonl_count = 0
    for src_dir in JSONL_SOURCES:
        for jsonl in src_dir.glob("*.jsonl"):
            results.append(upload_file(bucket, jsonl, f"data/{jsonl.name}", dry_run))
            jsonl_count += 1
    if jsonl_count == 0:
        print("  ℹ️  No .jsonl files found")

    # Summary
    ok    = sum(1 for r in results if r.get("status") in ("ok", "dry_run"))
    total = len(results)
    total_mb = sum(r.get("size_mb", 0) for r in results)
    print(f"\n{'='*60}")
    print(f"  ✅ Upload complete: {ok}/{total} files ({total_mb:.1f} MB total)")
    print(f"  Browse: https://console.cloud.google.com/storage/browser/{BUCKET_NAME}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
