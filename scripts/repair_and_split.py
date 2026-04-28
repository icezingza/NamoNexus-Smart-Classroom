import json
import os
from pathlib import Path

def repair_and_split():
    input_file = Path("knowledge/tripitaka_main/master_v45_ready.json")
    output_dir = Path("knowledge/tripitaka_main/chunks")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading {input_file}...")
    try:
        # ลองอ่านแบบ utf-8 ตรงๆ ก่อน
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Detected {len(data)} large records.")
        
        # ฟังก์ชันสำหรับซ่อมแซม string ที่อาจจะพัง (ถ้าจำเป็น)
        # ในที่นี้ Get-Content แสดงผลเป็นต่างดาว แต่อาจจะเพราะ terminal
        # นะโมจะลองเซฟออกมาดูว่าเป็นยังไง
        
        for i in range(0, len(data), 100):
            chunk = data[i:i + 100]
            chunk_idx = (i // 100) + 1
            output_file = output_dir / f"chunk_{chunk_idx:02d}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
            if chunk_idx % 10 == 0:
                print(f"Saved chunk {chunk_idx}...")
                
        print("Done! Metadata split into 100-record chunks for easier processing.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    repair_and_split()
