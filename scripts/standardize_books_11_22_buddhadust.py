#!/usr/bin/env python3
"""
Standardize Buddhadust raw JSON → chunk format (Books 11-22)
Maps raw {uid, pali, english, title} → {chunk_id, title, text, source_url}
"""

import json
from pathlib import Path
import hashlib

RAW_DIR = Path("knowledge/tripitaka_main/books_11_22_raw")
OUTPUT_DIR = Path("knowledge/tripitaka_main/chunks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Book mapping (Buddhadust)
BOOK_MAP = {
    "DN": (11, 14),   # Books 11-14: Digha Nikaya
    "MN": (15, 18),   # Books 15-18: Majjhima Nikaya
    "SN": (19, 21),   # Books 19-21: Samyutta Nikaya
    "AN": (22, 22)    # Book 22: Anguttara Nikaya
}

BUDDHADUST_BASE = "https://www.buddhadust.com/dob"

def standardize_chunk(raw_sutta, nikaya_code, book_num):
    """Convert raw sutta → standard chunk format"""
    chunk_id = f"books_11_22_{nikaya_code}_{raw_sutta.get('uid', 'unknown')}"
    
    return {
        "chunk_id": chunk_id,
        "title": raw_sutta.get('title', f'{nikaya_code} Sutta'),
        "text": raw_sutta.get('english', ''),  # Fallback to english field
        "source_url": f"{BUDDHADUST_BASE}/{nikaya_code.lower()}/{raw_sutta.get('uid', '')}.html",
        "book": book_num,
        "nikaya": nikaya_code,
        "source": "buddhadust.com"
    }

def main():
    all_chunks = []
    
    for nikaya_code in ["DN", "MN", "SN", "AN"]:
        book_start, book_end = BOOK_MAP[nikaya_code]
        raw_file = RAW_DIR / f"{nikaya_code}_raw.json"
        
        if not raw_file.exists():
            print(f"⚠️  {raw_file} not found, skipping {nikaya_code}")
            continue
        
        with open(raw_file, 'r', encoding='utf-8') as f:
            suttas = json.load(f)
        
        print(f"📖 {nikaya_code}: Processing {len(suttas)} suttas")
        
        for sutta in suttas:
            # All suttas in a Nikaya get same book number (e.g., all DN → book 11)
            chunk = standardize_chunk(sutta, nikaya_code, book_start)
            all_chunks.append(chunk)
        
        print(f"   ✅ Standardized {len(suttas)} chunks")
    
    # Save standardized chunks
    output_file = OUTPUT_DIR / "chunk_books_11_22.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved {len(all_chunks)} chunks to {output_file}")
    print(f"✅ Standardization complete!")

if __name__ == "__main__":
    main()
