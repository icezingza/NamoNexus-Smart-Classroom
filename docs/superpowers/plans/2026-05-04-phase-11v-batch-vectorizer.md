# Phase 11V: Batch Vectorizer — Global Library Expansion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vectorize 23 books (1,310 chunks) from `knowledge/global_library/` into per-book FAISS indexes, register them as a secondary knowledge source, and verify quality with audit.

**Architecture:** `batch_vectorizer.py` generates one `.index` + `_metadata.json` per book into `knowledge/tripitaka_main/batch_indexes/`. These are kept **separate** from the main Tripitaka index (different model: `paraphrase-multilingual-MiniLM-L12-v2` vs `all-MiniLM-L6-v2`) to prevent embedding-space contamination. A new `GlobalLibraryRetriever` wraps all per-book indexes for unified search. RAM is monitored throughout.

**Tech Stack:** Python 3.11, FAISS (`faiss-cpu`), `sentence-transformers`, `psutil` (RAM monitor), existing `knowledge_service.py` pattern

---

## ⚠️ Critical Risk: Model Mismatch

| Index | Model | Dim | Space |
|-------|-------|-----|-------|
| `tripitaka_main/tripitaka_index.faiss` | `all-MiniLM-L6-v2` | 384 | L6 embedding |
| `batch_indexes/*.index` | `paraphrase-multilingual-MiniLM-L12-v2` | 384 | L12 embedding |

**Rule: NEVER merge batch_indexes into tripitaka_index.** Query each separately.

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Run (existing) | `scripts/batch_vectorizer.py` | Vectorize global_library → batch_indexes/ |
| Create | `scripts/audit_batch_indexes.py` | Audit new per-book indexes |
| Create | `backend/namo_core/services/knowledge/global_library_retriever.py` | Search across all batch_indexes |
| Modify | `backend/namo_core/services/knowledge/knowledge_service.py` | Add global_library as secondary search path |
| Create | `backend/namo_core/tests/unit/test_global_library_retriever.py` | Unit tests for retriever |

---

## Task 1: Pre-flight — Model & RAM Baseline

**Files:**
- Run: `scripts/batch_vectorizer.py` (read-only inspection)

- [ ] **Step 1: Verify model is cached (avoid mid-run download)**

```bash
cd C:\Users\icezi\NamoNexus-Smart-Classroom
.venv\Scripts\python.exe -c "
from sentence_transformers import SentenceTransformer
import time
print('Checking model cache...')
t = time.time()
m = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print(f'Model ready in {time.time()-t:.1f}s')
test = m.encode(['test'], show_progress_bar=False)
print(f'Encode OK — dim={test.shape[1]}')
"
```

Expected output: `Model ready in <3s` (cached) or downloads once (~420 MB first time).

- [ ] **Step 2: Record RAM baseline**

```bash
.venv\Scripts\python.exe -c "
import psutil, os
proc = psutil.Process(os.getpid())
vm = psutil.virtual_memory()
print(f'System RAM: {vm.used/1024**3:.2f}GB used / {vm.total/1024**3:.2f}GB total')
print(f'Available: {vm.available/1024**3:.2f}GB')
# Estimate: 1310 chunks * 384 dims * 4 bytes = ~2MB FAISS + ~5MB model = negligible
print(f'Estimated additional FAISS size: ~2 MB for 1310 vectors')
"
```

Expected: Available RAM > 2 GB (safe to proceed).

- [ ] **Step 3: Verify all 23 JSON files have `content` field**

```bash
.venv\Scripts\python.exe -c "
import json
from pathlib import Path
issues = []
total = 0
for f in sorted(Path('knowledge/global_library').glob('*.json')):
    d = json.loads(f.read_text(encoding='utf-8'))
    if not isinstance(d, list):
        issues.append(f'{f.name}: not a list')
        continue
    no_content = [i for i,x in enumerate(d) if not x.get('content','').strip()]
    total += len(d)
    if no_content:
        issues.append(f'{f.name}: {len(no_content)} records missing content')
print(f'Total chunks: {total}')
print(f'Issues: {issues if issues else \"NONE — all clear\"}')
"
```

Expected: `Total chunks: 1310`, `Issues: NONE`.

- [ ] **Step 4: Commit baseline check (no code changes)**

```bash
git add -A
git status
# Nothing to commit at this point — pre-flight is read-only
```

---

## Task 2: Run Batch Vectorizer with RAM Monitor

**Files:**
- Run: `scripts/batch_vectorizer.py`
- Output: `knowledge/tripitaka_main/batch_indexes/*.index` + `*_metadata.json`

- [ ] **Step 1: Run with inline RAM monitoring**

```bash
.venv\Scripts\python.exe -c "
import subprocess, psutil, threading, time, sys

peak_ram = [0]
done = [False]

def monitor():
    while not done[0]:
        used = psutil.virtual_memory().used / 1024**2
        if used > peak_ram[0]:
            peak_ram[0] = used
        time.sleep(0.5)

t = threading.Thread(target=monitor, daemon=True)
t.start()

t0 = time.time()
result = subprocess.run(
    [r'.venv\Scripts\python.exe', 'scripts/batch_vectorizer.py'],
    capture_output=False
)
done[0] = True

elapsed = time.time() - t0
print(f'\n--- Run Complete ---')
print(f'Exit code: {result.returncode}')
print(f'Total time: {elapsed:.1f}s')
print(f'Peak RAM during run: {peak_ram[0]:.0f} MB')
"
```

Expected:
- 23 books processed, no `[Error]` lines
- Exit code: `0`
- Peak RAM: < 2 GB (1,310 vectors at 384-dim ≈ 2 MB FAISS, model ≈ 420 MB)

- [ ] **Step 2: Verify output files exist**

```bash
.venv\Scripts\python.exe -c "
from pathlib import Path
idx_dir = Path('knowledge/tripitaka_main/batch_indexes')
indexes = sorted(idx_dir.glob('*.index'))
metas = sorted(idx_dir.glob('*_metadata.json'))
print(f'Index files:    {len(indexes)} (expected 23)')
print(f'Metadata files: {len(metas)} (expected 23)')
total_size = sum(f.stat().st_size for f in indexes) / 1024**2
print(f'Total index size: {total_size:.2f} MB')
for f in indexes:
    print(f'  {f.name}: {f.stat().st_size/1024:.1f} KB')
"
```

Expected: 23 `.index` files, 23 `_metadata.json` files, total size ~2-5 MB.

---

## Task 3: Audit New Batch Indexes

**Files:**
- Create: `scripts/audit_batch_indexes.py`

- [ ] **Step 1: Create audit script**

```python
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
    print("  Batch Index Audit — Global Library")
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
    print(f"  Count match:    {'YES' if not mismatches else f'MISMATCH in {[m[\"file\"] for m in mismatches]}'}")
    print(f"  Empty chunks:   {total_empty}")
    print(f"  Short (<50):    {total_short} ({total_short/total_chunks*100:.1f}%)")
    print(f"  HTML leaks:     {total_html}")
    print("=" * 60)
    if total_empty == 0 and total_html == 0 and not mismatches:
        print("  PASS — Global Library indexes are clean.")
    else:
        print("  WARN — Review issues above before production use.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run audit**

```bash
cd C:\Users\icezi\NamoNexus-Smart-Classroom
.venv\Scripts\python.exe scripts/audit_batch_indexes.py
```

Expected: All books `[OK]`, `Empty chunks: 0`, `HTML leaks: 0`, `Count match: YES`.

- [ ] **Step 3: Commit audit script + results**

```bash
git add scripts/audit_batch_indexes.py knowledge/tripitaka_main/batch_indexes/
git commit -m "feat: [NN-P11V] add global_library batch indexes and audit script"
```

---

## Task 4: GlobalLibraryRetriever — Secondary Search Path

**Files:**
- Create: `backend/namo_core/services/knowledge/global_library_retriever.py`
- Modify: `backend/namo_core/services/knowledge/knowledge_service.py`
- Create: `backend/namo_core/tests/unit/test_global_library_retriever.py`

- [ ] **Step 1: Write failing test**

```python
# backend/namo_core/tests/unit/test_global_library_retriever.py
import pytest
from unittest.mock import patch, MagicMock
import numpy as np


def test_retriever_returns_results_for_valid_query():
    from namo_core.services.knowledge.global_library_retriever import GlobalLibraryRetriever
    retriever = GlobalLibraryRetriever.__new__(GlobalLibraryRetriever)
    retriever.books = [
        {
            "index": MagicMock(**{"ntotal": 2, "search.return_value": (
                np.array([[0.9, 0.8]]),
                np.array([[0, 1]])
            )}),
            "metadata": [
                {"content": "ธรรมะคือความจริง", "title": "บทที่ 1", "book": "test"},
                {"content": "ศีลทำให้จิตสงบ", "title": "บทที่ 2", "book": "test"},
            ],
        }
    ]
    retriever.model = MagicMock(
        encode=MagicMock(return_value=np.array([[0.1] * 384]))
    )

    results = retriever.search("ธรรมะ", top_k=2)

    assert len(results) == 2
    assert results[0]["content"] == "ธรรมะคือความจริง"
    assert results[0]["score"] >= results[1]["score"]


def test_retriever_returns_empty_for_no_books():
    from namo_core.services.knowledge.global_library_retriever import GlobalLibraryRetriever
    retriever = GlobalLibraryRetriever.__new__(GlobalLibraryRetriever)
    retriever.books = []
    retriever.model = MagicMock(encode=MagicMock(return_value=np.array([[0.1] * 384])))

    results = retriever.search("test", top_k=5)
    assert results == []
```

- [ ] **Step 2: Run test to confirm failure**

```bash
cd C:\Users\icezi\NamoNexus-Smart-Classroom
.venv\Scripts\python.exe -m pytest backend/namo_core/tests/unit/test_global_library_retriever.py -v
```

Expected: `ModuleNotFoundError: No module named 'namo_core.services.knowledge.global_library_retriever'`

- [ ] **Step 3: Implement GlobalLibraryRetriever**

```python
# backend/namo_core/services/knowledge/global_library_retriever.py
"""Search across per-book FAISS indexes from global_library batch vectorization.

NOTE: These indexes use paraphrase-multilingual-MiniLM-L12-v2 (L12 embedding space).
Do NOT merge with tripitaka_index.faiss (all-MiniLM-L6-v2 / L6 space).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_BATCH_DIR = Path(__file__).resolve().parents[4] / "knowledge" / "tripitaka_main" / "batch_indexes"


class GlobalLibraryRetriever:
    def __init__(self) -> None:
        logger.info("GlobalLibraryRetriever: loading model %s", _MODEL_NAME)
        self.model = SentenceTransformer(_MODEL_NAME)
        self.books: list[dict] = []
        self._load_indexes()

    def _load_indexes(self) -> None:
        if not _BATCH_DIR.exists():
            logger.warning("batch_indexes dir not found: %s", _BATCH_DIR)
            return
        for meta_path in sorted(_BATCH_DIR.glob("*_metadata.json")):
            index_path = _BATCH_DIR / meta_path.name.replace("_metadata.json", ".index")
            if not index_path.exists():
                logger.warning("Missing index for %s — skipped", meta_path.name)
                continue
            try:
                index = faiss.read_index(str(index_path))
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                self.books.append({"index": index, "metadata": metadata})
            except Exception as exc:
                logger.error("Failed to load %s: %s", index_path.name, exc)
        logger.info("GlobalLibraryRetriever: loaded %d book indexes", len(self.books))

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.books:
            return []
        vec = self.model.encode([query], normalize_embeddings=True).astype("float32")
        all_hits: list[dict] = []
        for book in self.books:
            n = min(top_k, book["index"].ntotal)
            if n == 0:
                continue
            scores, indices = book["index"].search(vec, n)
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue
                item = dict(book["metadata"][idx])
                item["score"] = float(score)
                all_hits.append(item)
        all_hits.sort(key=lambda x: x["score"], reverse=True)
        return all_hits[:top_k]
```

- [ ] **Step 4: Run test to confirm pass**

```bash
.venv\Scripts\python.exe -m pytest backend/namo_core/tests/unit/test_global_library_retriever.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Wire into knowledge_service as secondary source**

In `backend/namo_core/services/knowledge/knowledge_service.py`, find the `search` method and add fallback to global library. Add after the existing Tripitaka results block:

```python
# At top of file, add import:
from namo_core.services.knowledge.global_library_retriever import GlobalLibraryRetriever

# Inside KnowledgeService.__init__, add:
self._global_lib: GlobalLibraryRetriever | None = None

# Add property:
@property
def global_lib(self) -> GlobalLibraryRetriever:
    if self._global_lib is None:
        self._global_lib = GlobalLibraryRetriever()
    return self._global_lib
```

Then in the search method, append global library hits after Tripitaka results (with label):

```python
# After tripitaka results are assembled, append:
if settings.enable_knowledge:
    try:
        gl_hits = self.global_lib.search(query, top_k=3)
        for hit in gl_hits:
            hit["source"] = "global_library"
        results.extend(gl_hits)
    except Exception as exc:
        logger.warning("GlobalLibrary search failed: %s", exc)
```

- [ ] **Step 6: Commit retriever + integration**

```bash
git add backend/namo_core/services/knowledge/global_library_retriever.py \
        backend/namo_core/services/knowledge/knowledge_service.py \
        backend/namo_core/tests/unit/test_global_library_retriever.py
git commit -m "feat: [NN-P11V] add GlobalLibraryRetriever as secondary RAG source"
```

---

## Self-Review

### Spec Coverage
| Requirement | Task |
|-------------|------|
| Run batch_vectorizer.py | Task 2 |
| RAM monitoring | Task 2 Step 1 |
| Audit new indexes (count, quality, short chunks) | Task 3 |
| Register as retrieval source | Task 4 |
| No merge into Tripitaka index | Risk section + Task 4 retriever design |

### Placeholder Scan
- No TBD/TODO in code blocks ✅
- All file paths exact ✅
- All method signatures consistent across tasks ✅
- `GlobalLibraryRetriever.search()` signature consistent in test + impl ✅

### Type Consistency
- `search(query: str, top_k: int) -> list[dict]` — consistent in test mock, impl, and knowledge_service call ✅
- `self.books: list[dict]` — consistent between test setup and `_load_indexes` ✅
