# -*- coding: utf-8 -*-
"""
batch_vectorizer.py -- Namo Core Automatic Batch Embedding Generator
===================================================================
Automates the conversion of clean JSON books into FAISS vectors.
Part of the SMART (AI-Resonance) Pillar.
"""

import os
import json
import time
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# --- Config ---
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
INPUT_DIR = Path("knowledge/global_library")
OUTPUT_DIR = Path("knowledge/tripitaka_main/batch_indexes")
DIMENSION = 384  # For MiniLM-L12

class BatchVectorizer:
    def __init__(self):
        print(f"[Init] Loading Model: {MODEL_NAME}...")
        self.model = SentenceTransformer(MODEL_NAME)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def process_file(self, file_path: Path):
        print(f"\n[Process] Reading: {file_path.name}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract text chunks (assuming the clean JSON format has 'content' or similar)
        # Adjust based on your actual JSON structure
        chunks = []
        if isinstance(data, list):
            chunks = [item.get('content', '') for item in data if item.get('content')]
        
        if not chunks:
            print(f"  [Skip] No valid content found in {file_path.name}")
            return

        print(f"  [AI] Encoding {len(chunks)} chunks...")
        t0 = time.time()
        embeddings = self.model.encode(chunks, show_progress_bar=True)
        
        # Create FAISS Index
        index = faiss.IndexFlatIP(DIMENSION)
        faiss.normalize_L2(embeddings)
        index.add(embeddings.astype('float32'))

        # Save Index & Metadata
        base_name = file_path.stem
        index_file = OUTPUT_DIR / f"{base_name}.index"
        meta_file = OUTPUT_DIR / f"{base_name}_metadata.json"

        faiss.write_index(index, str(index_file))
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        elapsed = time.time() - t0
        print(f"  [Done] Saved to {index_file.name} ({elapsed:.1f}s)")

    def run_all(self):
        json_files = sorted(INPUT_DIR.glob("*.json"))
        print(f"[Start] Found {len(json_files)} books to vectorize.")
        
        for f in json_files:
            try:
                self.process_file(f)
            except Exception as e:
                print(f"  [Error] Failed to process {f.name}: {e}")

if __name__ == "__main__":
    vectorizer = BatchVectorizer()
    vectorizer.run_all()
