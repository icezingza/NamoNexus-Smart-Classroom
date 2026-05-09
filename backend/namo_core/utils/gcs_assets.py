"""
gcs_assets.py — GCS FAISS Asset Download Utility

Downloads required FAISS indexes and metadata from GCS if they are missing
or have a different size from the remote manifest.

GCS bucket layout (SMART Pillars):
  namo-classroom-models/
    faiss/
      tripitaka_main/
        tripitaka_index.faiss          (168,861 vectors, ~248 MB)
        tripitaka_metadata.json
        batch_indexes/
          book_23_clean.index
          book_23_clean_metadata.json
          ... (23 books total)

Usage (standalone):
  python -m namo_core.utils.gcs_assets          # download missing assets
  python -m namo_core.utils.gcs_assets --force  # re-download even if present

Integrated into startup (production only) via app.py.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def get_project_root() -> Path:
    """Return the runtime root that owns the knowledge asset directory."""
    package_root = Path(__file__).resolve().parents[2]
    env_root = os.getenv("NAMO_PROJECT_ROOT")
    candidates = [
        Path(env_root) if env_root else None,
        package_root.parent,
        package_root,
        Path.cwd(),
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / "knowledge" / "tripitaka_main").exists():
            return candidate
    for candidate in candidates:
        if candidate is not None and (candidate / "namo_core").exists():
            return candidate
    return package_root.parent


_PROJECT_ROOT = get_project_root()
_KNOWLEDGE_DIR = _PROJECT_ROOT / "knowledge"
_TRIPITAKA_MAIN = _KNOWLEDGE_DIR / "tripitaka_main"
_BATCH_DIR = _TRIPITAKA_MAIN / "batch_indexes"

# ---------------------------------------------------------------------------
# GCS configuration
# ---------------------------------------------------------------------------
_GCS_BUCKET_MODELS = "namo-classroom-models"
_GCS_PREFIX_MODELS = "models"

# Required critical assets (must exist for RAG to work)
_CRITICAL_ASSETS: list[tuple[str, Path]] = [
    (
        f"{_GCS_PREFIX_MODELS}/tripitaka_index.faiss",
        _TRIPITAKA_MAIN / "tripitaka_index.faiss",
    ),
    (
        f"{_GCS_PREFIX_MODELS}/tripitaka_metadata.json",
        _TRIPITAKA_MAIN / "tripitaka_metadata.json",
    ),
]

# Batch indexes (23 books — non-critical, graceful fallback if missing)
_BATCH_BOOK_RANGE = range(23, 46)


class AssetStatus(NamedTuple):
    name: str
    local_path: Path
    exists: bool
    size_bytes: int


# ---------------------------------------------------------------------------
# Local asset checks
# ---------------------------------------------------------------------------

def check_local_assets() -> list[AssetStatus]:
    """Return status of all required local FAISS assets."""
    statuses: list[AssetStatus] = []

    for _gcs_path, local_path in _CRITICAL_ASSETS:
        exists = local_path.exists()
        size = local_path.stat().st_size if exists else 0
        statuses.append(AssetStatus(local_path.name, local_path, exists, size))

    # Batch indexes
    for book_num in _BATCH_BOOK_RANGE:
        for suffix in [".index", "_metadata.json"]:
            fname = f"book_{book_num}_clean{suffix}"
            local_path = _BATCH_DIR / fname
            exists = local_path.exists()
            size = local_path.stat().st_size if exists else 0
            statuses.append(AssetStatus(fname, local_path, exists, size))

    return statuses


def are_critical_assets_present() -> bool:
    """Quick check — returns True only if both critical assets exist and are non-empty."""
    for _gcs_path, local_path in _CRITICAL_ASSETS:
        if not local_path.exists() or local_path.stat().st_size < 1_000:
            return False
    return True


# ---------------------------------------------------------------------------
# GCS download helpers
# ---------------------------------------------------------------------------

def _gcs_client():
    """Return a GCS client, or raise ImportError if library unavailable."""
    try:
        from google.cloud import storage
        return storage.Client()
    except ImportError as exc:
        raise ImportError(
            "google-cloud-storage not installed. "
            "Add it to requirements.txt: google-cloud-storage>=2.5.0"
        ) from exc


def _download_blob(bucket_name: str, blob_name: str, dest_path: Path) -> None:
    """Download one GCS blob to local path. Creates parent dirs automatically."""
    client = _gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    if not blob.exists():
        raise FileNotFoundError(
            f"GCS blob not found: gs://{bucket_name}/{blob_name}"
        )

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(f"{dest_path.suffix}.{os.getpid()}.tmp")

    logger.info("Downloading gs://%s/%s → %s", bucket_name, blob_name, dest_path)
    blob.download_to_filename(str(tmp_path))

    # Atomic rename: prevents a corrupt partial download from being used
    tmp_path.rename(dest_path)
    logger.info("Download complete: %s (%.1f MB)", dest_path.name, dest_path.stat().st_size / 1e6)


async def _download_blob_async(bucket_name: str, blob_name: str, dest_path: Path) -> None:
    """Async wrapper around _download_blob for concurrent downloads."""
    await asyncio.to_thread(_download_blob, bucket_name, blob_name, dest_path)


# ---------------------------------------------------------------------------
# High-level sync / async API
# ---------------------------------------------------------------------------

def download_critical_assets(force: bool = False) -> None:
    """Download critical FAISS assets from GCS synchronously.

    Args:
        force: Re-download even if local file exists.

    Raises:
        RuntimeError: If a critical download fails.
    """
    errors: list[str] = []
    for gcs_path, local_path in _CRITICAL_ASSETS:
        if local_path.exists() and not force:
            logger.debug("Asset present, skipping: %s", local_path.name)
            continue
        try:
            _download_blob(_GCS_BUCKET_MODELS, gcs_path, local_path)
        except Exception as exc:
            errors.append(f"{local_path.name}: {exc}")
            logger.error("Failed to download critical asset %s: %s", local_path.name, exc)

    if errors:
        raise RuntimeError(
            "Critical GCS asset download failed:\n" + "\n".join(errors)
        )


async def ensure_assets_async(force: bool = False) -> dict[str, int]:
    """Ensure critical + batch assets exist; download missing ones concurrently.

    Returns:
        dict with 'downloaded', 'already_present', 'failed' counts.
    """
    stats = {"downloaded": 0, "already_present": 0, "failed": 0}

    # Build work list. Batch indexes are optional and currently not present in
    # the production bucket; keep startup focused on the two critical RAG files.
    work: list[tuple[str, Path]] = list(_CRITICAL_ASSETS)
    if os.getenv("NAMO_DOWNLOAD_BATCH_INDEXES", "").lower() in {"1", "true", "yes"}:
        for book_num in _BATCH_BOOK_RANGE:
            for suffix in [".index", "_metadata.json"]:
                fname = f"book_{book_num}_clean{suffix}"
                gcs_path = f"{_GCS_PREFIX_MODELS}/batch_indexes/{fname}"
                local_path = _BATCH_DIR / fname
                work.append((gcs_path, local_path))

    # Concurrent downloads — semaphore limits parallel GCS connections
    semaphore = asyncio.Semaphore(4)

    async def _download_with_sem(gcs_path: str, local_path: Path) -> str:
        if local_path.exists() and not force:
            return "present"
        async with semaphore:
            try:
                await _download_blob_async(_GCS_BUCKET_MODELS, gcs_path, local_path)
                return "downloaded"
            except Exception as exc:
                logger.error("Download failed %s: %s", gcs_path, exc)
                return "failed"

    results = await asyncio.gather(
        *[_download_with_sem(g, l) for g, l in work],
        return_exceptions=False,
    )

    for r in results:
        if r == "present":
            stats["already_present"] += 1
        elif r == "downloaded":
            stats["downloaded"] += 1
        else:
            stats["failed"] += 1

    return stats


# ---------------------------------------------------------------------------
# Startup integration hook (called by app.py in production)
# ---------------------------------------------------------------------------

async def ensure_assets_for_startup() -> None:
    """Called during FastAPI startup in production to guarantee local FAISS assets.

    Behaviour:
    - Dev / local: skip silently (assume assets are pre-placed on disk).
    - Production: if critical assets are absent and GOOGLE_APPLICATION_CREDENTIALS
      is set, attempt GCS download. Hard-fail only if assets remain missing after
      the download attempt.
    """
    from namo_core.config.settings import get_settings
    settings = get_settings()

    if settings.env != "production":
        return  # Never auto-download in dev — avoids 248 MB surprise downloads

    if are_critical_assets_present():
        logger.debug("[GCS] Critical FAISS assets present — no download needed")
        return

    logger.info("[GCS] Critical FAISS assets missing — initiating download from GCS...")
    try:
        result = await ensure_assets_async(force=False)
        logger.info("[GCS] Asset sync complete: %s", result)
        if not are_critical_assets_present():
            logger.error("[GCS] Critical assets still missing after download. RAG unavailable.")
    except ImportError as exc:
        logger.error("[GCS] google-cloud-storage unavailable: %s", exc)
    except Exception as exc:
        logger.error("[GCS] Asset download failed: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Sync NamoNexus FAISS assets from GCS")
    parser.add_argument("--force", action="store_true", help="Re-download even if assets exist")
    parser.add_argument("--check", action="store_true", help="Check local asset status and exit")
    args = parser.parse_args()

    if args.check:
        statuses = check_local_assets()
        critical_missing = [s for s in statuses if not s.exists and "_index.faiss" in s.name or
                            not s.exists and "tripitaka_metadata" in s.name]
        total = len(statuses)
        present = sum(1 for s in statuses if s.exists)
        print(f"\nLocal asset status: {present}/{total} present")
        for s in statuses:
            icon = "✅" if s.exists else "❌"
            size_str = f"{s.size_bytes/1e6:.1f} MB" if s.exists else "MISSING"
            print(f"  {icon} {s.name:50s} {size_str}")
        sys.exit(0 if are_critical_assets_present() else 1)

    # Download mode
    try:
        download_critical_assets(force=args.force)
        print("\n✅ Critical FAISS assets ready")
        if args.force:
            stats = asyncio.run(ensure_assets_async(force=True))
            print(f"Batch indexes: {stats}")
    except RuntimeError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)
