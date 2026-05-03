# scripts/audit_batch_indexes.py
"""Audit quality of per-book FAISS indexes from global_library."""
import json
import re
from pathlib import Path

import faiss
import numpy as np

BATCH_DIR = Path("knowledge/tripitaka_main/batch_indexes")
SHORT_THRESHOLD = 50
HTML_PATTERN = re.compile(r"<[a-zA-Z][^>]*>")


def audit_book(meta_path: Path) -> dict:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return {"file": meta_path.stem, "error": "not a list"}

    texts = [item.get("content", "") for item in data]
    total = len(texts)
    empty = sum(1 for t in texts if not t.strip())
    short = sum(1 for t in texts if 0 < len(t.strip()) < SHORT_THRESHOLD)
    html = sum(1 for t in texts if HTML_PATTERN.search(t))
    avg_len = sum(len(t) for t in texts) / total if total else 0

    index_path = BATCH_DIR / meta_path.name.replace("_metadata.json", ".index")
    index = faiss.read_index(str(index_path))
    vector_count = index.ntotal

    return {
        "file": meta_path.stem.replace("_metadata", ""),
        "chunks": total,
        "vectors": vector_count,
        "count_match": total == vector_count,
        "avg_len": round(avg_len, 1),
        "empty": empty,
        "short": short,
        "html": html,
    }


def main():
    meta_files = sorted(BATCH_DIR.glob("*_metadata.json"))
    if not meta_files:
        print("No metadata files found. Run batch_vectorizer.py first.")
        return

    print("=" * 60)
    print("  Batch Index Audit -- Global Library")
    print("=" * 60)

    results = [audit_book(f) for f in meta_files]

    total_chunks = sum(r.get("chunks", 0) for r in results)
    total_vectors = sum(r.get("vectors", 0) for r in results)
    total_short = sum(r.get("short", 0) for r in results)
    total_html = sum(r.get("html", 0) for r in results)
    total_empty = sum(r.get("empty", 0) for r in results)
    mismatches = [r for r in results if not r.get("count_match")]

    for r in results:
        status = "OK" if r.get("count_match") and r.get("html", 0) == 0 and r.get("empty", 0) == 0 else "WARN"
        print(f"  [{status}] {r['file']}: {r.get('chunks')} chunks, avg {r.get('avg_len')} chars, short={r.get('short')}")

    print()
    print(f"  Total chunks:   {total_chunks}")
    print(f"  Total vectors:  {total_vectors}")
    mismatch_files = [m["file"] for m in mismatches]
    print(f"  Count match:    {'YES' if not mismatches else 'MISMATCH in ' + str(mismatch_files)}")
    print(f"  Empty chunks:   {total_empty}")
    print(f"  Short (<50):    {total_short} ({total_short/total_chunks*100:.1f}%)")
    print(f"  HTML leaks:     {total_html}")
    print("=" * 60)
    if total_empty == 0 and total_html == 0 and not mismatches:
        print("  PASS -- Global Library indexes are clean.")
    else:
        print("  WARN -- Review issues above before production use.")


if __name__ == "__main__":
    main()
