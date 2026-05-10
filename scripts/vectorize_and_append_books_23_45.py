#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vectorize Books 23-45 and append to existing FAISS index
Input: chunks/chunk_books_23_45.json (1,453 standardized chunks)
Output: Updated tripitaka_index.faiss (170,087 → ~171,540 vectors)
"""

import json
import faiss
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import time

def vectorize_and_append(
    chunks_file: str = "knowledge/tripitaka_main/chunks/chunk_books_23_45.json",
    index_path: str = "knowledge/tripitaka_main/tripitaka_index.faiss",
    metadata_file: str = "knowledge/tripitaka_main/metadata.json",
    model_name: str = "sentence-transformers/sentence-multilingual-minilm-l12-v2",
    batch_size: int = 32
) -> Dict[str, Any]:
    """Vectorize Books 23-45 chunks and append to existing FAISS index"""
    
    print("📂 Loading chunks...")
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"✓ Loaded {len(chunks)} chunks")
    
    print(f"📇 Loading existing FAISS index ({index_path})...")
    index = faiss.read_index(index_path)
    initial_vectors = index.ntotal
    print(f"✓ Existing index: {initial_vectors} vectors")
    
    print("🤖 Loading SentenceTransformer (384-dim)...")
    model = SentenceTransformer(model_name)
    
    print(f"🔤 Generating embeddings (batch_size={batch_size})...")
    texts = [chunk['text'] for chunk in chunks]
    
    start_time = time.time()
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        batch_size=batch_size
    )
    elapsed = time.time() - start_time
    
    print(f"✓ Generated {len(embeddings)} embeddings")
    print(f"   Shape: {embeddings.shape} | Time: {elapsed:.1f}s | Avg: {elapsed/len(chunks)*1000:.1f}ms/chunk")
    
    print("🔗 Appending vectors to FAISS index...")
    index.add(embeddings.astype(np.float32))
    
    final_vectors = index.ntotal
    added_vectors = final_vectors - initial_vectors
    print(f"✓ Index updated: {initial_vectors} → {final_vectors} (+{added_vectors})")
    
    print(f"💾 Saving updated FAISS index...")
    faiss.write_index(index, index_path)
    
    print(f"📝 Updating metadata.json...")
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    metadata['total_vectors'] = final_vectors
    metadata['books_coverage'] = list(range(1, 46))  # Books 1-45
    metadata['last_update'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    if 'integration_status' not in metadata:
        metadata['integration_status'] = {}
    
    metadata['integration_status'].update({
        'phase': 'books_23_45_complete',
        'books_23_45': {
            'status': 'vectorized',
            'chunks_processed': len(chunks),
            'vectors_added': added_vectors,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
    })
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print("\n✅ Complete")
    print(f"   Initial: {initial_vectors} | Added: {added_vectors} | Final: {final_vectors}")
    print(f"   Time: {elapsed:.1f}s | Rate: {len(chunks)/elapsed:.1f} chunks/s")
    
    return {
        "initial_vectors": initial_vectors,
        "added_vectors": added_vectors,
        "final_vectors": final_vectors,
        "chunks_processed": len(chunks),
        "vectorization_time_seconds": elapsed,
        "index_path": str(Path(index_path).absolute())
    }

if __name__ == "__main__":
    result = vectorize_and_append()
    print(f"\n📁 Output: {result['index_path']}")
