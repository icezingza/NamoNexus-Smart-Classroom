"""
upload_to_gcs.py — Namo Core FAISS & Knowledge Backup to GCS
Usage: python upload_to_gcs.py
Env  : GCS_BUCKET, GOOGLE_APPLICATION_CREDENTIALS
"""
import os, sys, hashlib, json
from pathlib import Path
from datetime import datetime

try:
    from google.cloud import storage
except ImportError:
    print("ERROR: pip install google-cloud-storage")
    sys.exit(1)

BUCKET_NAME = os.getenv("GCS_BUCKET", "namo-classroom")
KEY_FILE    = os.getenv("GOOGLE_APPLICATION_CREDENTIALS",
                         r"C:\\Users\\icezi\\Downloads\\Github repo\\namo_core_project\\namo_core_key.json")
LOCAL_ROOT  = Path(r"C:\\Users\\icezi\\Downloads\\Github repo\\namo_core_project\\backend\\namo_core")

FILES_TO_UPLOAD = [
    ("knowledge/tripitaka/tripitaka_index.faiss",    "models/tripitaka_index.faiss"),
    ("knowledge/tripitaka/tripitaka_metadata.json",  "models/tripitaka_metadata.json"),
]

JSONL_HOME = Path(r"C:\\Users\\icezi")
JSONL_PATTERN = "*.jsonl"

def md5(path: Path, chunk=1<<20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk_data := f.read(chunk): h.update(chunk_data)
    return h.hexdigest()

def upload(client, bucket, local: Path, remote: str):
    blob = bucket.blob(remote)
    size_mb = local.stat().st_size / (1024*1024)
    print(f"  Uploading {local.name} ({size_mb:.1f} MB) -> gs://{BUCKET_NAME}/{remote}")
    blob.upload_from_filename(str(local))
    blob.metadata = {"md5": md5(local), "uploaded": datetime.utcnow().isoformat()}
    blob.patch()
    print(f"  ✅ Done")

def main():
    print(f"\nNamo Core GCS Upload — {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}")
    print(f"Bucket  : {BUCKET_NAME}")
    print(f"Key     : {KEY_FILE}\n")
    client = storage.Client.from_service_account_json(KEY_FILE)
    bucket = client.bucket(BUCKET_NAME)
    if not bucket.exists(): bucket.create(location="asia-southeast1"); print("✅ Bucket created")
    for local_rel, remote_path in FILES_TO_UPLOAD:
        local = LOCAL_ROOT / local_rel
        if local.exists(): upload(client, bucket, local, remote_path)
        else: print(f"  ⚠️  SKIP (not found): {local}")
    for jsonl in JSONL_HOME.glob(JSONL_PATTERN):
        upload(client, bucket, jsonl, f"data/{jsonl.name}")
    print("\n✅ GCS Upload complete")

if __name__ == "__main__":
    main()
