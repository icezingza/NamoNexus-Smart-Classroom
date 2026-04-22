"""
master_ingestion.py - ภารกิจฝังรากฐานความรู้ (FAISS Indexing)
=========================================================
ทำหน้าที่นำข้อมูลที่นะโม 2 ชำระแล้ว มาสร้างเป็นดัชนีเวกเตอร์
เพื่อให้ระบบ RAG ของนะโมค้นหาข้อมูลได้แม่นยำและรวดเร็ว
"""

import json
import os
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# --- Config ---
SOURCE_FILE = Path("knowledge/tripitaka_v25_distributed.json")
INDEX_DIR = Path("knowledge/tripitaka")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

def run_ingestion():
    print(f"🚀 เริ่มกระบวนการฝังรากฐานความรู้จาก {SOURCE_FILE}...")
    
    if not SOURCE_FILE.exists():
        print(f"❌ ไม่พบไฟล์ข้อมูล: {SOURCE_FILE}")
        return

    # 1. โหลดข้อมูล
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # ใช้อาเรย์เก็บ Content เพื่อทำ Embedding
    texts = [item.get('content', '') for item in data if item.get('content')]
    # กรองเฉพาะรายการที่มีเนื้อหา
    metadatas = [item for item in data if item.get('content')]
    
    print(f"📥 โหลดข้อมูลสำเร็จ {len(texts)} รายการ")

    # 2. โหลด Embedding Model
    print(f"🧠 กำลังโหลดสมอง AI: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    # 3. สร้าง Embeddings
    print("⚡ กำลังคำนวณเวกเตอร์ความหมาย (Embeddings)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    embeddings = embeddings.astype('float32')
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    # 4. สร้าง FAISS Index
    print("🏗️ กำลังสร้างดัชนี FAISS...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension) # Inner Product on normalized vectors = Cosine Similarity
    index.add(embeddings)

    # 5. บันทึกผล
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    faiss.write_index(index, str(INDEX_DIR / "tripitaka_index.faiss"))
    
    with open(INDEX_DIR / "tripitaka_metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadatas, f, ensure_ascii=False, indent=2)
        
    print(f"\n✨ สำเร็จ! สร้างดัชนีความรู้เรียบร้อยที่ {INDEX_DIR}")
    print(f"📊 สรุป: {index.ntotal} เวกเตอร์, มิติ {dimension}")

if __name__ == "__main__":
    run_ingestion()
