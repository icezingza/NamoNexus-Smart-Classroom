#!/usr/bin/env python3
"""
Standardize Books 11-22 from SuttaCentral raw → chunk format
Match Books 1-10 structure
"""
import json
from pathlib import Path

def standardize_books_11_22():
    raw_dir = Path("knowledge/tripitaka_main/books_11_22_raw")
    out_file = Path("knowledge/tripitaka_main/chunks/chunk_books_11_22.json")
    
    chunks = []
    chunk_id_counter = 0
    
    NIKAYA_BOOKS = {
        "DN": (11, "Digha Nikaya"),
        "MN": (15, "Majjhima Nikaya"),
        "SN": (19, "Samyutta Nikaya"),
        "AN": (22, "Anguttara Nikaya"),
    }
    
    print("🔄 Standardizing Books 11-22...")
    print("=" * 70)
    
    for nikaya, (start_book, name) in NIKAYA_BOOKS.items():
        raw_file = raw_dir / f"{nikaya}_raw.json"
        if not raw_file.exists():
            print(f"⚠️  {raw_file} not found - skipping {nikaya}")
            continue
        
        with open(raw_file, encoding="utf-8") as f:
            suttas = json.load(f)
        
        print(f"\n📄 Processing {nikaya}: {len(suttas)} suttas")
        
        for sutta in suttas:
            pali_text = sutta.get("pali", "").strip()
            if not pali_text:
                continue
            
            chunk = {
                "chunk_id": f"v{start_book:02d}_p{chunk_id_counter:04d}_c000",
                "title": sutta.get("title", f"{name} - {sutta.get('uid', 'unknown')}"),
                "text": pali_text,
                "source_url": f"https://suttacentral.net/{sutta.get('uid', '')}/pli/ms",
            }
            chunks.append(chunk)
            chunk_id_counter += 1
        
        print(f"   ✅ Standardized {len(suttas)} suttas")
    
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Standardization complete!")
    print(f"   Total chunks: {len(chunks)}")
    print(f"   Output: {out_file}")

if __name__ == "__main__":
    standardize_books_11_22()
