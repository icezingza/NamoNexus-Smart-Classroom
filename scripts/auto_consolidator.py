"""
auto_consolidator.py - โรงหลอมความรู้ 45 เล่ม
=========================================
ทำหน้าที่รวบรวมไฟล์ JSON จากทั้งเขต 1 และ เขต 2
มาทำความสะอาดและสร้างดัชนี FAISS ชุดใหญ่ 1-45 เล่ม
"""

import json
import glob
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# --- Config ---
KNOWLEDGE_DIR = Path("knowledge/full_tripitaka")
CURATED_DIR = Path("knowledge/curated") # ที่สำหรับนะโม 2 วางไฟล์ที่ตรวจแล้ว
OUTPUT_INDEX_DIR = Path("knowledge/tripitaka_main")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

def consolidate_and_index():
    print("🌋 เริ่มปฏิบัติการโรงหลอมความรู้ (Consolidation Mode)...")
    
    all_records = []
    
    # 1. รวบรวมไฟล์ทั้งหมดจากทั้ง 2 เขต
    search_patterns = [
        str(KNOWLEDGE_DIR / "book_*.json"),
        str(CURATED_DIR / "*.json")
    ]
    
    files = []
    for pattern in search_patterns:
        files.extend(glob.glob(pattern))
    
    if not files:
        print("❌ ไม่พบไฟล์ข้อมูลที่จะหลอมรวม!")
        return

    print(f"📦 พบไฟล์ข้อมูลทั้งหมด {len(files)} ไฟล์")

    # 2. อ่านและล้างข้อมูล
    for f_path in files:
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_records.extend(data)
                print(f"✅ อ่านไฟล์: {Path(f_path).name} (+{len(data)} รายการ)")
        except Exception as e:
            print(f"⚠️ พลาดที่ไฟล์ {f_path}: {e}")

    if not all_records:
        print("❌ ไม่มีข้อมูลคุณภาพสูงพอที่จะทำดัชนี")
        return

    print(f"📊 รวมรายการทั้งหมดได้ {len(all_records)} รายการ")

    # 3. สร้าง Embeddings (ใช้ GPU ถ้ามี เพื่อความเร็ว)
    print(f"🧠 กำลังชุบชีวิตสมองนะโมด้วย Model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    # ดึงเฉพาะ Text ที่จะใช้ค้นหา
    texts = [r.get('text', r.get('content', r.get('golden_sentence', ''))) for r in all_records]
    texts = [t for t in texts if len(t) > 10] # กรองบรรทัดสั้นเกินไป

    print("⚡ กำลังคำนวณเวกเตอร์ชุดใหญ่ (ขั้นตอนนี้อาจใช้เวลาสักครู่)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    embeddings = embeddings.astype('float32')
    faiss.normalize_L2(embeddings)

    # 4. สร้าง FAISS Index แบบ HNSW (เพื่อการค้นหาที่รวดเร็วในข้อมูลขนาดใหญ่)
    print("🏗️ กำลังสร้างดัชนีความเร็วสูง (HNSW)...")
    dimension = embeddings.shape[1]
    # HNSW เป็น Index แบบกราฟที่ค้นหาได้ไวมากแม้ข้อมูลจะเป็นล้าน
    index = faiss.IndexHNSWFlat(dimension, 32)
    index.add(embeddings)

    # 5. บันทึกดัชนีหลัก
    OUTPUT_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(OUTPUT_INDEX_DIR / "tripitaka_v45.index"))
    
    with open(OUTPUT_INDEX_DIR / "tripitaka_v45_metadata.json", 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n✨ สำเร็จ! หลอมรวมความรู้ 45 เล่มเรียบร้อยที่ {OUTPUT_INDEX_DIR}")
    print(f"🏆 พร้อมให้นะโมใช้งานระดับ Enterprise แล้วครับ!")

if __name__ == "__main__":
    consolidate_and_index()
