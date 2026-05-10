# -*- coding: utf-8 -*-
"""
vectorize_books_11_22.py — Phase 3b: Append Books 11-22 chunks into main FAISS index
Reads chunk_books_11_22.json, embeds with MiniLM, appends to tripitaka_index.faiss
"""

import json
import sys
import time
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# -- Config --
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_FILE = Path("knowledge/tripitaka_main/chunks/chunk_books_11_22.json")
INDEX_FILE = Path("knowledge/tripitaka_main/tripitaka_index.faiss")
META_FILE  = Path("knowledge/tripitaka_main/tripitaka_metadata.json")
BATCH_SIZE = 256
MIN_CHARS  = 50  # hard quality gate

def configure_utf8():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

def load_chunks(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def quality_filter(chunks: list[dict]) -> list[dict]:
    passed = [c for c in chunks if len(c.get("text", "").strip()) >= MIN_CHARS]
    print(f"  Quality filter: {len(chunks)} → {len(passed)} chunks ({len(chunks)-len(passed)} dropped)")
    return passed

def embed_chunks(model: SentenceTransformer, chunks: list[dict]) -> np.ndarray:
    texts = [c["text"] for c in chunks]
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        print(f"  Embedding batch {i//BATCH_SIZE + 1}/{(len(texts)-1)//BATCH_SIZE + 1} ({len(batch)} chunks)...")
        emb = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
        all_embeddings.append(emb)
    return np.vstack(all_embeddings).astype("float32")

def normalize_for_metadata(chunks: list[dict]) -> list[dict]:
    return [
        {
            "chunk_id": c.get("chunk_id", f"books_11_22_{i}"),
            "title": c.get("title", ""),
            "text": c.get("text", ""),
            "source_url": c.get("source_url", ""),
        }
        for i, c in enumerate(chunks)
    ]

def main():
    configure_utf8()
    t_start = time.time()

    print(f"[1/5] Loading chunks from {CHUNK_FILE}...")
    raw_chunks = load_chunks(CHUNK_FILE)
    print(f"  Loaded: {len(raw_chunks)} chunks")

    print("[2/5] Applying quality filter...")
    chunks = quality_filter(raw_chunks)

    print(f"[3/5] Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print(f"[4/5] Embedding {len(chunks)} chunks...")
    embeddings = embed_chunks(model, chunks)
    faiss.normalize_L2(embeddings)
    print(f"  Embeddings shape: {embeddings.shape}")

    print("[5/5] Appending to FAISS index + metadata...")
    index = faiss.read_index(str(INDEX_FILE))
    before = index.ntotal
    index.add(embeddings)
    after = index.ntotal
    faiss.write_index(index, str(INDEX_FILE))
    print(f"  FAISS: {before} → {after} vectors (+{after - before})")

    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    metadata.extend(normalize_for_metadata(chunks))
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=None)
    print(f"  Metadata: {len(metadata)} total records")

    elapsed = time.time() - t_start
    print(f"\n✅ Phase 3b Complete — {after} total vectors ({elapsed:.1f}s)")
    print(f"   FAISS: {INDEX_FILE}")
    print(f"   Metadata: {META_FILE}")

if __name__ == "__main__":
    main()
