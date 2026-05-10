#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standardize Books 23-45 from tripitaka_v45_metadata.json to chunk format
Input: tripitaka_v45_metadata.json (1,453 records)
Output: chunks/chunk_books_23_45.json
"""

import json
from pathlib import Path
from typing import List, Dict, Any

def get_nikaya_from_book(book: int) -> str:
    """Map book number to nikaya"""
    if 1 <= book <= 10:
        return "Sutta Pitaka"
    elif 11 <= book <= 14:
        return "Digha Nikaya"
    elif 15 <= book <= 18:
        return "Majjhima Nikaya"
    elif 19 <= book <= 21:
        return "Samyutta Nikaya"
    elif book == 22:
        return "Anguttara Nikaya"
    elif 23 <= book <= 45:
        return "Vinaya & Abhidhamma"
    return "Unknown"

def standardize_books_23_45(
    input_file: str = "knowledge/tripitaka_main/tripitaka_v45_metadata.json",
    output_file: str = "knowledge/tripitaka_main/chunks/chunk_books_23_45.json"
) -> Dict[str, Any]:
    """
    Standardize Books 23-45 metadata to chunk format
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    print(f"📖 Reading {input_path.name}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        records = json.load(f)

    print(f"✓ Loaded {len(records)} records")

    chunks: List[Dict[str, Any]] = []
    chunk_id_counter = 0

    for record in records:
        book = record.get('book', 0)
        item_id = record.get('item_id', 0)
        title = record.get('title', '').strip()
        content = record.get('content', '').strip()

        # Skip empty records
        if not title or not content:
            continue

        chunk_id_counter += 1
        chunk_id = f"chunk_books_23_45_{chunk_id_counter:05d}"

        chunk = {
            "chunk_id": chunk_id,
            "title": title,
            "text": content,
            "book": book,
            "nikaya": get_nikaya_from_book(book),
            "source": "tripitaka_v45_metadata.json",
            "item_id": item_id
        }
        chunks.append(chunk)

    print(f"📝 Standardized {len(chunks)} chunks")

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"💾 Writing to {output_file}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    # Summary stats
    books_coverage = set(chunk['book'] for chunk in chunks)
    nikaya_breakdown = {}
    for chunk in chunks:
        nikaya = chunk['nikaya']
        nikaya_breakdown[nikaya] = nikaya_breakdown.get(nikaya, 0) + 1

    summary = {
        "total_chunks": len(chunks),
        "books_covered": sorted(list(books_coverage)),
        "books_count": len(books_coverage),
        "nikaya_breakdown": nikaya_breakdown,
        "avg_chunk_length": sum(len(c['text']) for c in chunks) // len(chunks) if chunks else 0,
        "output_file": str(output_path)
    }

    print("\n✅ Standardization Complete")
    print(f"   Total chunks: {summary['total_chunks']}")
    print(f"   Books covered: {summary['books_count']}")
    print(f"   Nikaya breakdown: {summary['nikaya_breakdown']}")
    print(f"   Avg chunk length: {summary['avg_chunk_length']} chars")

    return summary

if __name__ == "__main__":
    result = standardize_books_23_45()
    print(f"\n📁 Output: {result['output_file']}")
