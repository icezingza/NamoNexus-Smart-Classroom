"""
seed_cache.py - ภารกิจป้อนความจำด่วน (Semantic Cache Priming)
=========================================================
นำชุดคำถาม-คำตอบที่คุณนะโม 2 คัดสรรมา ป้อนเข้าสู่ฐานข้อมูล
Semantic Cache เพื่อการตอบสนองที่ไวที่สุด
"""

import json
from pathlib import Path
from sqlalchemy.orm import Session
from namo_core.database.core import SessionLocal, engine, Base
from namo_core.database.models import SemanticCacheEntry
from namo_core.services.knowledge.semantic_cache_repository import SemanticCacheRepository

# --- Config ---
QA_FILE = Path("knowledge/classroom_mock_qa.json")

def seed_semantic_cache():
    print(f"⚡ เริ่มปฏิบัติการป้อนความจำด่วนจาก {QA_FILE}...")
    
    # สร้างตารางถ้ายังไม่มี (Phase 12 Integration)
    Base.metadata.create_all(bind=engine)
    
    if not QA_FILE.exists():
        print(f"❌ ไม่พบไฟล์คำถาม-คำตอบ: {QA_FILE}")
        return

    with open(QA_FILE, 'r', encoding='utf-8') as f:
        qa_data = json.load(f)

    db = SessionLocal()
    # repo = SemanticCacheRepository() # ไม่ต้องสร้าง object เพราะเป็น staticmethod
    
    added_count = 0
    for item in qa_data:
        query = item['question']
        # จำลองโครงสร้าง response ของนะโม
        response = {
            "answer": item['answer'],
            "source": f"Tripitaka Vol 25 (ID: {item.get('source_id')})",
            "curriculum": "General Wisdom"
        }
        
        # บันทึกลง Cache ผ่าน static method
        try:
            SemanticCacheRepository.save_cache_entry(db, query.strip().lower(), response)
            print(f"✅ เพิ่มลง Cache: {query[:50]}...")
            added_count += 1
        except Exception as e:
            print(f"❌ พลาดที่ข้อความ '{query[:30]}': {e}")

    db.close()
    print(f"\n✨ สำเร็จ! ป้อนความจำด่วนเรียบร้อย {added_count} รายการ")

if __name__ == "__main__":
    seed_semantic_cache()
