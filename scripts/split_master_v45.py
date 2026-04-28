import json
import os
from pathlib import Path
from collections import defaultdict

def split_master_v45():
    # Config
    input_file = Path("knowledge/tripitaka_main/master_v45_ready.json")
    output_dir = Path("knowledge/full_tripitaka")
    records_per_chunk = 100
    
    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    print(f"Loading {input_file} (This might take a moment due to 273MB size)...")
    
    # Load the big file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total records found: {len(data)}")

    # Group by book
    books_data = defaultdict(list)
    for item in data:
        book_id = item.get("book")
        if book_id is not None:
            books_data[book_id].append(item)

    print(f"Found {len(books_data)} unique books.")

    total_chunks = 0
    # Split each book into chunks
    for book_id, items in books_data.items():
        # Sort items by item_id just in case
        items.sort(key=lambda x: x.get("item_id", 0))
        
        chunk_count = 0
        for i in range(0, len(items), records_per_chunk):
            chunk_items = items[i : i + records_per_chunk]
            chunk_id = (i // records_per_chunk) + 1
            
            output_filename = f"book_{book_id:02d}_chunk_{chunk_id:03d}.json"
            output_path = output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(chunk_items, out_f, ensure_ascii=False, indent=2)
            
            chunk_count += 1
            total_chunks += 1
        
        print(f"  Book {book_id:02d}: Split into {chunk_count} chunks.")

    print(f"\nSuccess! Total {total_chunks} chunk files created in {output_dir}")

if __name__ == "__main__":
    split_master_v45()
