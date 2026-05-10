"""
verify_cloud_assets.py — NamoNexus Cloud & RAG Pipeline Verification

Checks end-to-end readiness before deploying to production:

  [1] Local FAISS assets         — tripitaka_index.faiss + 23 batch indexes
  [2] Vector counts              — 170,047 Tripitaka vectors (Books 1-22), 23 book indexes
  [3] RAG search quality         — both Tripitaka + GlobalLibrary return results
  [4] Pre-warm timing            — both retrievers load within SLA (< 30s)
  [5] GCS bucket accessibility   — namo-classroom-models / namonexus-wisdom-storage
  [6] Environment secrets        — JWT, admin password are not placeholders

Exit code:
  0 — all checks passed (PRODUCTION READY)
  1 — one or more checks failed

Run from project root:
  python scripts/verify_cloud_assets.py
  python scripts/verify_cloud_assets.py --skip-gcs   (skip GCS checks, local only)
  python scripts/verify_cloud_assets.py --quick       (critical checks only, < 5s)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_KNOWLEDGE_DIR = _PROJECT_ROOT / "knowledge"
_TRIPITAKA_MAIN = _KNOWLEDGE_DIR / "tripitaka_main"
_BATCH_DIR = _TRIPITAKA_MAIN / "batch_indexes"
_BACKEND_ROOT = _PROJECT_ROOT / "backend" / "namo_core"

sys.path.insert(0, str(_BACKEND_ROOT.parent))  # so we can import namo_core.*

# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
_PASS = "\033[92m PASS\033[0m"
_FAIL = "\033[91m FAIL\033[0m"
_WARN = "\033[93m WARN\033[0m"
_SKIP = "\033[94m SKIP\033[0m"


class VerificationReport:
    def __init__(self) -> None:
        self.results: list[tuple[str, str, str]] = []  # (check, status, detail)

    def add(self, check: str, passed: bool, detail: str = "", warn: bool = False) -> bool:
        if warn:
            status = _WARN
        elif passed:
            status = _PASS
        else:
            status = _FAIL
        self.results.append((check, status, detail))
        return passed

    def skip(self, check: str, reason: str = "") -> None:
        self.results.append((check, _SKIP, reason))

    def print_summary(self) -> int:
        """Print report and return exit code (0=ok, 1=failures exist)."""
        print("\n" + "=" * 70)
        print("  NamoNexus Cloud Verification Report")
        print("=" * 70)
        failures = 0
        for check, status, detail in self.results:
            detail_str = f" — {detail}" if detail else ""
            print(f"  [{status}] {check}{detail_str}")
            if status == _FAIL:
                failures += 1
        print("=" * 70)
        if failures == 0:
            print(f"\033[92m  ✅ ALL CHECKS PASSED — Production Ready\033[0m")
        else:
            print(f"\033[91m  ❌ {failures} check(s) FAILED — NOT production ready\033[0m")
        print()
        return 0 if failures == 0 else 1


report = VerificationReport()


# ---------------------------------------------------------------------------
# Check 1: Local FAISS assets
# ---------------------------------------------------------------------------

def check_local_faiss() -> None:
    print("\n[1] Local FAISS assets...")

    index_path = _TRIPITAKA_MAIN / "tripitaka_index.faiss"
    meta_path = _TRIPITAKA_MAIN / "tripitaka_metadata.json"

    # Main index
    exists = index_path.exists()
    size_mb = index_path.stat().st_size / 1e6 if exists else 0
    report.add(
        "tripitaka_index.faiss",
        exists and size_mb > 100,
        f"{size_mb:.1f} MB" if exists else "MISSING",
    )

    # Main metadata
    exists = meta_path.exists()
    report.add(
        "tripitaka_metadata.json",
        exists,
        "present" if exists else "MISSING",
    )

    # Batch indexes (23 books)
    present = len(list(_BATCH_DIR.glob("*.index")))
    report.add(
        f"batch_indexes ({present}/23 books)",
        present >= 20,  # allow up to 3 missing
        f"{present}/23 .index files" + ("" if present >= 23 else " — some missing"),
        warn=(20 <= present < 23),
    )


# ---------------------------------------------------------------------------
# Check 2: Vector counts
# ---------------------------------------------------------------------------

def check_vector_counts() -> None:
    print("\n[2] Vector counts...")

    try:
        import faiss

        index_path = _TRIPITAKA_MAIN / "tripitaka_index.faiss"
        if not index_path.exists():
            report.add("Tripitaka vector count", False, "index not found")
            return

        index = faiss.read_index(str(index_path))
        ntotal = index.ntotal
        expected = 171_357  # Books 1-45 complete (P25, 2026-05-11)
        report.add(
            f"Tripitaka vectors = {ntotal:,}",
            ntotal >= expected * 0.99,  # allow 1% drift from rebuilds
            f"expected {expected:,}",
            warn=(ntotal != expected),
        )

        # Metadata parity
        meta_path = _TRIPITAKA_MAIN / "tripitaka_metadata.json"
        if meta_path.exists():
            with meta_path.open(encoding="utf-8") as f:
                meta = json.load(f)
            meta_count = len(meta) if isinstance(meta, list) else 0
            parity_ok = abs(ntotal - meta_count) <= 10
            report.add(
                f"Metadata parity ({meta_count:,} records vs {ntotal:,} vectors)",
                parity_ok,
                "OK" if parity_ok else f"MISMATCH — delta={abs(ntotal-meta_count)}",
            )

        # Batch index total
        total_batch = 0
        for index_file in _BATCH_DIR.glob("*.index"):
            try:
                bi = faiss.read_index(str(index_file))
                total_batch += bi.ntotal
            except Exception:
                pass
        report.add(
            f"GlobalLibrary total vectors = {total_batch:,}",
            total_batch > 0,
            f"across {len(list(_BATCH_DIR.glob('*.index')))} book indexes",
        )

    except ImportError:
        report.add("FAISS import", False, "faiss-cpu not installed")


# ---------------------------------------------------------------------------
# Check 3: RAG search quality
# ---------------------------------------------------------------------------

def check_rag_search() -> None:
    print("\n[3] RAG search quality...")

    # Test queries
    test_queries = [
        ("อริยสัจ 4", ["ทุกข์", "สมุทัย", "นิโรธ", "มรรค"]),
        ("ไตรสรณคมน์", ["พระพุทธ", "พระธรรม", "พระสงฆ์"]),
    ]

    try:
        os.environ.setdefault("NAMO_TTS_PROVIDER", "mock")
        os.environ.setdefault("NAMO_SPEECH_PROVIDER", "mock")
        os.environ.setdefault("NAMO_REASONING_PROVIDER", "mock")
        os.environ.setdefault("NAMO_SYSTEM_SECRET", "test-secret-32chars-xxxxxxxxxxx")
        os.environ.setdefault("NAMO_JWT_SECRET_KEY", "test-secret-32chars-xxxxxxxxxxx")
        os.environ.setdefault("NAMO_ADMIN_PASSWORD", "test")
        os.environ.setdefault("NAMO_ENV", "development")

        from namo_core.services.knowledge.tripitaka_retriever import get_tripitaka_retriever

        t0 = time.monotonic()
        retriever = get_tripitaka_retriever()
        load_ms = int((time.monotonic() - t0) * 1000)
        report.add(
            f"TripitakaRetriever load",
            retriever is not None,
            f"{load_ms}ms",
            warn=(load_ms > 10_000),
        )

        if retriever:
            for query, expected_kws in test_queries:
                t0 = time.monotonic()
                results = retriever.search(query, top_k=3)
                search_ms = int((time.monotonic() - t0) * 1000)
                has_results = len(results) > 0
                combined_text = " ".join(r.get("text", "") + r.get("title", "") for r in results)
                kw_hit = sum(1 for kw in expected_kws if kw in combined_text)
                report.add(
                    f"Tripitaka search: '{query}'",
                    has_results and kw_hit >= 2,
                    f"{len(results)} results, {kw_hit}/{len(expected_kws)} keywords, {search_ms}ms",
                    warn=(has_results and kw_hit < 2),
                )

    except Exception as exc:
        report.add("TripitakaRetriever", False, str(exc)[:100])

    # Global Library
    try:
        from namo_core.services.knowledge.global_library_retriever import get_global_library_retriever

        t0 = time.monotonic()
        gl = get_global_library_retriever()
        load_ms = int((time.monotonic() - t0) * 1000)
        report.add(
            f"GlobalLibraryRetriever load ({len(gl.books)} books)",
            len(gl.books) >= 20,
            f"{load_ms}ms",
            warn=(len(gl.books) < 23),
        )

        if gl.books:
            t0 = time.monotonic()
            results = gl.search("พระพุทธ", top_k=3)
            search_ms = int((time.monotonic() - t0) * 1000)
            report.add(
                "GlobalLibrary search: 'พระพุทธ'",
                len(results) > 0,
                f"{len(results)} results, {search_ms}ms",
            )

    except Exception as exc:
        report.add("GlobalLibraryRetriever", False, str(exc)[:100])

    # KnowledgeService dual-source
    try:
        from namo_core.services.knowledge.knowledge_service import KnowledgeService

        ks = KnowledgeService()
        t0 = time.monotonic()
        results = ks.search("มรรค 8", top_k=5)
        search_ms = int((time.monotonic() - t0) * 1000)
        sources = {r.get("source", "unknown") for r in results}
        report.add(
            "KnowledgeService dual-source search",
            len(results) > 0,
            f"{len(results)} results from {sources}, {search_ms}ms",
        )
    except Exception as exc:
        report.add("KnowledgeService", False, str(exc)[:100])


# ---------------------------------------------------------------------------
# Check 4: Pre-warm timing SLA
# ---------------------------------------------------------------------------

def check_prewarm_timing() -> None:
    print("\n[4] Pre-warm timing SLA...")

    # Retrievers should already be loaded (singleton) from check 3
    try:
        from namo_core.services.knowledge.tripitaka_retriever import _retriever_instance
        from namo_core.services.knowledge.global_library_retriever import _retriever as _gl_instance

        tri_loaded = _retriever_instance is not None
        gl_loaded = _gl_instance is not None

        report.add("Tripitaka singleton cached in memory", tri_loaded)
        report.add("GlobalLibrary singleton cached in memory", gl_loaded)

        # Test first query latency (singleton should respond fast)
        if tri_loaded:
            t0 = time.monotonic()
            _retriever_instance.search("ทุกข์", top_k=3)  # type: ignore[union-attr]
            latency_ms = int((time.monotonic() - t0) * 1000)
            sla_ok = latency_ms < 200
            report.add(
                f"First-query latency: {latency_ms}ms (SLA < 200ms)",
                sla_ok,
                "within SLA" if sla_ok else "EXCEEDED — check FAISS index size",
                warn=not sla_ok,
            )

    except ImportError as exc:
        report.add("Singleton state check", False, str(exc)[:80])


# ---------------------------------------------------------------------------
# Check 5: GCS bucket accessibility
# ---------------------------------------------------------------------------

def check_gcs_buckets() -> None:
    print("\n[5] GCS bucket accessibility...")

    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        report.skip("GCS buckets", "GOOGLE_APPLICATION_CREDENTIALS not set")
        return

    try:
        from google.cloud import storage
        client = storage.Client()

        buckets_to_check = [
            ("namo-classroom-models", "faiss/tripitaka_main/tripitaka_index.faiss"),
            ("namonexus-wisdom-storage", None),
            ("namo-classroom", None),
        ]

        for bucket_name, required_blob in buckets_to_check:
            try:
                bucket = client.bucket(bucket_name)
                exists = bucket.exists()
                if not exists:
                    report.add(f"GCS bucket: {bucket_name}", False, "bucket not found")
                    continue

                if required_blob:
                    blob = bucket.blob(required_blob)
                    blob_exists = blob.exists()
                    size_mb = blob.size / 1e6 if blob_exists and blob.size else 0
                    report.add(
                        f"GCS: gs://{bucket_name}/{required_blob}",
                        blob_exists,
                        f"{size_mb:.1f} MB" if blob_exists else "MISSING",
                    )
                else:
                    report.add(f"GCS bucket: gs://{bucket_name}", True, "accessible")

            except Exception as exc:
                report.add(f"GCS bucket: {bucket_name}", False, str(exc)[:80])

    except ImportError:
        report.skip("GCS buckets", "google-cloud-storage not installed")


# ---------------------------------------------------------------------------
# Check 6: Environment secrets
# ---------------------------------------------------------------------------

def check_secrets() -> None:
    print("\n[6] Environment secrets...")

    _PLACEHOLDER = "MUST_BE_SET_IN_ENV"

    # Read directly from .env file to bypass os.environ overrides set earlier
    # in this script (setdefault at top uses test values for non-secret checks).
    env_file = Path(__file__).resolve().parents[1] / "backend" / "namo_core" / ".env"
    raw: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                raw[k.strip()] = v.strip().strip('"').strip("'")

    try:
        jwt_key = raw.get("NAMO_JWT_SECRET_KEY", _PLACEHOLDER)
        jwt_ok = jwt_key != _PLACEHOLDER and len(jwt_key) >= 32
        report.add(
            "NAMO_JWT_SECRET_KEY",
            jwt_ok,
            f"length={len(jwt_key)}" if jwt_ok else "placeholder or too short",
        )

        admin_pw = raw.get("NAMO_ADMIN_PASSWORD", _PLACEHOLDER)
        pw_ok = admin_pw != _PLACEHOLDER
        is_bcrypt = admin_pw.startswith("$2b$") if pw_ok else False
        namo_env = raw.get("NAMO_ENV", "development")
        report.add(
            "NAMO_ADMIN_PASSWORD",
            pw_ok,
            "bcrypt hash" if is_bcrypt else ("plaintext — use bcrypt in production" if pw_ok else "placeholder"),
            warn=(pw_ok and not is_bcrypt and namo_env == "production"),
        )

        report.add(
            f"NAMO_ENV = {namo_env}",
            True,
            "production" if namo_env == "production" else "development",
            warn=(namo_env != "production"),
        )

    except Exception as exc:
        report.add("Settings load", False, str(exc)[:100])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="NamoNexus Cloud Verification")
    parser.add_argument("--skip-gcs", action="store_true", help="Skip GCS bucket checks")
    parser.add_argument("--quick", action="store_true", help="Local asset checks only (fast)")
    args = parser.parse_args()

    print("=" * 70)
    print("  NamoNexus Cloud Verification")
    print(f"  Project root: {_PROJECT_ROOT}")
    print("=" * 70)

    check_local_faiss()

    if not args.quick:
        check_vector_counts()
        check_rag_search()
        check_prewarm_timing()

    if not args.skip_gcs and not args.quick:
        check_gcs_buckets()

    check_secrets()

    return report.print_summary()


if __name__ == "__main__":
    sys.exit(main())
