import json
from pathlib import Path

def ultra_precise_chunker():
    input_file = Path("knowledge/tripitaka_main/master_v45_ready.json")
    output_dir = Path("knowledge/tripitaka_main/chunks_deep")
    target_count = 168861
    
    if not input_file.exists(): return

    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. วิเคราะห์ความยาวจริงทั้งหมด
    total_chars = sum(len(item.get("text", "")) for item in data)
    print(f"Total characters in dataset: {total_chars:,}")
    
    # 2. คำนวณ Chunk Size ที่ต้องใช้เพื่อให้ได้ target_count
    # (เราอาจต้องเผื่อเศษตอนจบแต่ละไอเทมด้วย นิดหน่อย)
    chunk_size = int(total_chars / target_count)
    print(f"Calculating precise chunk size: {chunk_size} characters")

    if not output_dir.exists(): output_dir.mkdir(parents=True)
    
    all_chunks = []
    for item in data:
        book_id = item.get("book", 0)
        item_id = item.get("item_id", 0)
        text = item.get("text", "")
        
        for i in range(0, len(text), chunk_size):
            content = text[i : i + chunk_size]
            c_idx = (i // chunk_size) + 1
            all_chunks.append({
                "chunk_id": f"b{book_id:02d}_i{item_id:04d}_c{c_idx:03d}",
                "book": book_id,
                "item_id": item_id,
                "title": item.get("title", ""),
                "text": content,
                "source_url": item.get("source_url", ""),
                "timestamp": item.get("timestamp", "")
            })

    print(f"Generated {len(all_chunks):,} chunks.")
    
    # บันทึก
    batch_size = 10000
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        f_num = (i // batch_size) + 1
        with open(output_dir / f"metadata_deep_part_{f_num:03d}.json", 'w', encoding='utf-8') as out_f:
            json.dump(batch, out_f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_chunks):,} records to {output_dir}")

if __name__ == "__main__":
    ultra_precise_chunker()
