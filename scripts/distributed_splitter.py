import json
import os
from pathlib import Path

def distributed_splitter():
    # Config
    input_file = Path("knowledge/tripitaka_main/master_v45_ready.json")
    output_dir = Path("knowledge/tripitaka_main/chunks")
    records_per_file = 5000 # ตามที่พี่ไอซ์สั่ง 5,000 - 10,000
    
    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        print(f"Created directory: {output_dir}")

    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_records = len(data)
    print(f"Total records to process: {total_records}")

    file_count = 0
    for i in range(0, total_records, records_per_file):
        chunk = data[i : i + records_per_file]
        file_count += 1
        
        output_path = output_dir / f"master_v45_part_{file_count:03d}.json"
        
        with open(output_path, 'w', encoding='utf-8') as out_f:
            json.dump(chunk, out_f, ensure_ascii=False, indent=2)
        
        print(f"  Saved: {output_path} ({len(chunk)} records)")

    print(f"\nDistributed Split Complete! Total {file_count} files in {output_dir}")

if __name__ == "__main__":
    distributed_splitter()
