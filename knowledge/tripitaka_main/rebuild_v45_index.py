"""
rebuild_v45_index.py — Rebuild FAISS index from master_v45_ready.json (all 5,494 records)

Problem fixed: Previous build only included books 2, 23-45 (1,453 records).
               Book 1 (4,041 records = 73.5% of master) was missing from index.

Run on Lenovo (with .venv activated):
    cd knowledge/tripitaka_main
    ..\..\..\.venv\Scripts\python.exe rebuild_v45_index.py
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
MASTER_FILE = SCRIPT_DIR / "master_v45_ready.json"
OUT_INDEX   = SCRIPT_DIR / "tripitaka_v45.index"
OUT_META    = SCRIPT_DIR / "tripitaka_v45_metadata.json"
BATCH_SIZE  = 256  # safe batch for sentence-transformers on Lenovo RAM

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def main() -> None:
    import numpy as np
    import faiss
    from sentence_transformers import SentenceTransformer

    # ── 1. Load master data ──────────────────────────────────────────────────
    logger.info("Loading %s ...", MASTER_FILE)
    with open(MASTER_FILE, encoding="utf-8") as f:
        records: list[dict] = json.load(f)

    logger.info("Total records in master: %d", len(records))

    # Validate field — master uses 'text', metadata used 'content'
    field = "text" if "text" in records[0] else "content"
    logger.info("Text field detected: '%s'", field)

    from collections import Counter
    book_dist = Counter(r.get("book", "?") for r in records)
    logger.info("Book distribution: %s", dict(sorted(book_dist.items())))

    # ── 2. Encode with SentenceTransformer ───────────────────────────────────
    logger.info("Loading embedding model: %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    texts: list[str] = [
        f"{r.get('title', '')} {r.get(field, '')}".strip()
        for r in records
    ]

    logger.info("Encoding %d texts in batches of %d ...", len(texts), BATCH_SIZE)
    t0 = time.perf_counter()
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # required for cosine similarity via IndexFlatIP
        convert_to_numpy=True,
    )
    elapsed = time.perf_counter() - t0
    logger.info("Encoding done in %.1fs. Shape: %s", elapsed, embeddings.shape)

    # ── 3. Build FAISS IndexFlatIP (cosine via L2-normalised vectors) ─────────
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    logger.info("FAISS index built: %d vectors, dim=%d", index.ntotal, dim)

    # ── 4. Backup old files ───────────────────────────────────────────────────
    for path in (OUT_INDEX, OUT_META):
        if path.exists():
            bak = path.with_suffix(path.suffix + ".bak_1453")
            path.rename(bak)
            logger.info("Backed up %s → %s", path.name, bak.name)

    # ── 5. Save index + metadata ──────────────────────────────────────────────
    faiss.write_index(index, str(OUT_INDEX))
    logger.info("Saved FAISS index → %s (%.1f MB)", OUT_INDEX.name, OUT_INDEX.stat().st_size / 1e6)

    # Normalise metadata to 'content' field for compatibility with tripitaka_retriever.py
    meta_out = [
        {
            "book":    r.get("book"),
            "item_id": r.get("item_id"),
            "title":   r.get("title", ""),
            "content": r.get(field, ""),   # normalise 'text' → 'content'
            "source":  r.get("source", "master_v45"),
        }
        for r in records
    ]
    with open(OUT_META, "w", encoding="utf-8") as f:
        json.dump(meta_out, f, ensure_ascii=False, indent=None)
    logger.info("Saved metadata → %s (%d records)", OUT_META.name, len(meta_out))

    # ── 6. Verify ─────────────────────────────────────────────────────────────
    assert index.ntotal == len(records), f"Mismatch: {index.ntotal} vs {len(records)}"
    logger.info("✅ DONE — index contains all %d records (เล่ม 1–2, 23–45)", index.ntotal)
    logger.info("Expected size: %.1f MB", index.ntotal * dim * 4 / 1e6)


if __name__ == "__main__":
    main()
