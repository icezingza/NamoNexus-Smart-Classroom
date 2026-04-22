"""
test_new_knowledge.py - ทดสอบความฉลาดของนะโมหลังอัปเกรดคลังความรู้
"""
import sys
import os
from pathlib import Path

# เพิ่ม Path เพื่อให้เรียกใช้ namo_core ได้
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from namo_core.services.knowledge.tripitaka_retriever import search_tripitaka

def test_rag_knowledge():
    queries = [
        "ไตรสรณคมน์คืออะไร",
        "ศีล 10 มีความหมายว่าอย่างไร",
        "อริยสัจ 4 และ ขันธ์ 5 เกี่ยวข้องกับอาหารอย่างไร"
    ]
    
    print("🔍 เริ่มการทดสอบระบบค้นหาความรู้ใหม่ (RAG Validation)...")
    print("="*60)
    
    for q in queries:
        print(f"คำถาม: {q}")
        results = search_tripitaka(q, top_k=1)
        if results:
            res = results[0]
            print(f"✅ พบข้อมูลอ้างอิง!")
            print(f"   หัวข้อ: {res.get('topic', res.get('title'))}")
            print(f"   ระดับชั้น: {res.get('curriculum_level', 'ไม่ระบุ')}")
            print(f"   แก่นธรรม: {res.get('text')[:200]}...")
        else:
            print("❌ ไม่พบข้อมูลที่เกี่ยวข้อง (อาจต้องปรับปรุงการ Embedding)")
        print("-" * 60)

if __name__ == "__main__":
    test_rag_knowledge()
