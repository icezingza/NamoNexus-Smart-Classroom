# -*- coding: utf-8 -*-
"""
vectorize_books_23_45.py — P25: Standardize + Vectorize Books 23-45
Source: knowledge/tripitaka_main/tripitaka_v45_metadata.json (Thai, MCU edition)
Appends to tripitaka_index.faiss + tripitaka_metadata.json
"""

import json
import sys
import time
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"
SOURCE_FILE = Path("knowledge/tripitaka_main/tripitaka_v45_metadata.json")
INDEX_FILE  = Path("knowledge/tripitaka_main/tripitaka_index.faiss")
META_FILE   = Path("knowledge/tripitaka_main/tripitaka_metadata.json")
CHUNK_OUT   = Path("knowledge/tripitaka_main/chunks/chunk_books_23_45.json")
BATCH_SIZE  = 256
MIN_CHARS   = 50
BOOK_RANGE  = range(23, 46)  # Books 23-45


def configure_utf8():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def load_and_filter(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Filter to Books 23-45 only
    filtered = [r for r in raw if r.get("book") in BOOK_RANGE]
    print(f"  Source records: {len(raw)} → Books 23-45: {len(filtered)}")

    # Quality gate
    passed = []
    for r in filtered:
        text = r.get("content", r.get("text", "")).strip()
        if len(text) >= MIN_CHARS:
            passed.append(r)
    print(f"  Quality filter: {len(filtered)} → {len(passed)} chunks")
    return passed


def to_chunk_format(records: list[dict]) -> list[dict]:
    chunks = []
    for r in records:
        text = r.get("content", r.get("text", "")).strip()
        book = r.get("book", 0)
        item = r.get("item_id", 0)
        chunks.append({
            "chunk_id": f"books_23_45_b{book:02d}_i{item:04d}",
            "title": r.get("title", f"Book {book} Item {item}"),
            "text": text,
            "source_url": r.get("source_url", f"https://84000.org/tipitaka/read/v.php?B={book}&A={item}"),
            "book": book,
            "source": "tripitaka_v45_mcu",
        })
    return chunks


def embed_chunks(model: SentenceTransformer, chunks: list[dict]) -> np.ndarray:
    texts = [c["text"] for c in chunks]
    all_emb = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        n = i // BATCH_SIZE + 1
        total = (len(texts) - 1) // BATCH_SIZE + 1
        print(f"  Batch {n}/{total} ({len(batch)} chunks)...")
        all_emb.append(model.encode(batch, show_progress_bar=False, convert_to_numpy=True))
    return np.vstack(all_emb).astype("float32")


def main():
    configure_utf8()
    t0 = time.time()

    print("[1/5] Loading + filtering Books 23-45...")
    records = load_and_filter(SOURCE_FILE)

    print("[2/5] Converting to chunk format...")
    chunks = to_chunk_format(records)
    CHUNK_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNK_OUT, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)
    print(f"  Saved {len(chunks)} chunks → {CHUNK_OUT}")

    print(f"[3/5] Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print(f"[4/5] Embedding {len(chunks)} chunks...")
    embeddings = embed_chunks(model, chunks)
    faiss.normalize_L2(embeddings)
    print(f"  Shape: {embeddings.shape}")

    print("[5/5] Appending to FAISS + metadata...")
    index = faiss.read_index(str(INDEX_FILE))
    before = index.ntotal
    index.add(embeddings)
    after = index.ntotal
    faiss.write_index(index, str(INDEX_FILE))
    print(f"  FAISS: {before:,} → {after:,} (+{after - before:,})")

    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    meta_records = [
        {
            "chunk_id": c["chunk_id"],
            "title": c["title"],
            "text": c["text"],
            "source_url": c["source_url"],
        }
        for c in chunks
    ]
    metadata.extend(meta_records)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)
    print(f"  Metadata: {len(metadata):,} total records")

    elapsed = time.time() - t0
    print(f"\n✅ P25 Complete — {after:,} total vectors ({elapsed:.1f}s)")
    print(f"   FAISS:    {INDEX_FILE}")
    print(f"   Metadata: {META_FILE}")
    print(f"   Chunks:   {CHUNK_OUT}")


if __name__ == "__main__":
    main()
