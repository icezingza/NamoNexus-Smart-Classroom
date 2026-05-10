#!/usr/bin/env python3
"""
Verify Books 11-22 integration completeness
"""
import json
from pathlib import Path
from collections import defaultdict

def verify_integration():
    knowledge_root = Path("knowledge/tripitaka_main")
    
    print("\n🔍 Books 11-22 Integration Verification")
    print("=" * 70)
    
    # Check if standardized chunk exists
    chunk_file = knowledge_root / "chunks" / "chunk_books_11_22.json"
    if chunk_file.exists():
        with open(chunk_file) as f:
            chunks = json.load(f)
        print(f"✅ Standardized chunks found: {len(chunks)} chunks")
        
        # Group by book
        books = defaultdict(int)
        for chunk in chunks:
            book_num = int(chunk["chunk_id"].split("_")[0][1:])
            books[book_num] += 1
        
        print(f"   Books: {dict(sorted(books.items()))}")
    else:
        print(f"❌ Standardized chunk file not found: {chunk_file}")
    
    # Check if FAISS index exists
    faiss_index = knowledge_root / "batch_indexes" / "books_11_22.index"
    if faiss_index.exists():
        size_mb = faiss_index.stat().st_size / (1024*1024)
        print(f"\n✅ FAISS index found: books_11_22.index ({size_mb:.1f} MB)")
    else:
        print(f"\n⚠️  FAISS index not created yet: {faiss_index}")
        print("   → Run: python3 scripts/batch_vectorizer.py --input chunks/chunk_books_11_22.json")
    
    # Check metadata update
    metadata_file = knowledge_root / "tripitaka_metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)
        
        total = len(metadata) if isinstance(metadata, list) else metadata.get("total_chunks", 0)
        print(f"\n📊 Metadata Status:")
        print(f"   Total chunks in metadata: {total}")
        
        if total > 170000:  # Should include new chunks
            print(f"   ✅ Metadata appears updated (includes Books 11-22)")
        else:
            print(f"   ⚠️  Metadata may not reflect new chunks yet")
    
    print(f"\n✅ Verification complete!")

if __name__ == "__main__":
    verify_integration()
