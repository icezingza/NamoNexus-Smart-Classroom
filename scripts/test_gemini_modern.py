import os
import sys
from pathlib import Path

# เพิ่ม Path เพื่อให้มองเห็น namo_core
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from namo_core.services.reasoning.gemini_modern_reasoner import GeminiModernReasoner

def test_drive():
    api_key = "AIzaSyBMuDg9jLpkY2ox8UQ7WIfmHNnGQdlkJDE"
    
    reasoner = GeminiModernReasoner(api_key=api_key)
    
    system_prompt = """
    # Role: นะโมเน็กซัส (NamoNexus)
    ท่านคือ "พี่นะโม" ปัญญาประดิษฐ์ผู้ใจดี รอบรู้พระไตรปิฎกเถรวาท
    1. สุภาพ นอบน้อม แทนตนเองว่า "พี่นะโม"
    2. ตอบอิงจาก context เท่านั้น
    3. ระบุเลขเล่มและหัวข้อเสมอ
    """
    
    context = [
        {
            "book": 1, 
            "item_id": 1, 
            "content": "สมัยนั้น พระผู้มีพระภาคพุทธเจ้าประทับอยู่ ณ ควงต้นสะเดาอันเป็นที่อยู่ของนเฬรุยักษ์ เขตเมืองเวรัญชา พร้อมกับภิกษุสงฆ์หมู่ใหญ่ประมาณ ๕๐๐ รูป"
        }
    ]
    
    query = "พี่นะโมครับ ในพระวินัยปิฎกเล่มที่ 1 พระพุทธเจ้าประทับอยู่ที่ไหนครับ?"
    
    print("\n🤖 [นะโมอัจฉริยะ 2.0 กำลังประมวลผลด้วยเทคโนโลยีล่าสุด...]\n")
    
    try:
        answer = reasoner.generate_dhamma_answer(query, context, system_prompt)
        print("-" * 60)
        print(f"คำถาม: {query}")
        print("-" * 60)
        print(f"คำตอบจากพี่นะโม 2.0:\n{answer}")
        print("-" * 60)
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    test_drive()
