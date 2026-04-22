import os
import sys
from pathlib import Path

# เพิ่ม Path เพื่อให้มองเห็น namo_core
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from namo_core.services.reasoning.gemini_reasoner import GeminiReasoner

def test_drive():
    # ตั้งค่าตัวแปรสภาพแวดล้อม
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "namo-classroom-58e4be305633.json"
    
    # ดึงค่า Project ID (ปกติอยู่ในไฟล์ JSON คีย์)
    project_id = "namo-classroom" 
    
    reasoner = GeminiReasoner(project_id=project_id)
    
    system_prompt = """
    # Role: นะโมเน็กซัส (NamoNexus) - โครงสร้างพื้นฐานเพื่อปัญญา
    ท่านคือ "นะโม" ปัญญาประดิษฐ์ผู้รอบรู้พระไตรปิฎกและคัมภีร์พุทธศาสนาเถรวาท ทำหน้าที่เป็นกัลยาณมิตร ครูผู้ใจดี และที่ปรึกษาทางปัญญาสำหรับเด็กและเยาวชน

    # Core Directive:
    1. สำรวมและถ่อมตน: ใช้ภาษาที่สุภาพ นอบน้อม แทนตนเองว่า "พี่นะโม" หรือ "นะโม"
    2. ความจริงเป็นเข็มทิศ: ตอบคำถามโดยอิงจาก context ที่ได้รับมาเท่านั้น
    3. อ้างอิงเสมอ: ทุกครั้งที่ตอบ ต้องระบุเลขเล่มและหัวข้อเสมอ (เช่น พระไตรปิฎก เล่ม 1 ข้อ 1)
    """
    
    context = [
        {
            "book": 1, 
            "item_id": 1, 
            "content": "สมัยนั้น พระผู้มีพระภาคพุทธเจ้าประทับอยู่ ณ ควงต้นสะเดาอันเป็นที่อยู่ของนเฬรุยักษ์ เขตเมืองเวรัญชา พร้อมกับภิกษุสงฆ์หมู่ใหญ่ประมาณ ๕๐๐ รูป"
        }
    ]
    
    query = "พี่นะโมครับ ในพระวินัยปิฎกเล่มที่ 1 พระพุทธเจ้าประทับอยู่ที่ไหนและมีใครอยู่ด้วยครับ?"
    
    print("\n🤖 [นะโมอัจฉริยะ กำลังประมวลผลผ่าน Google Cloud...]\n")
    
    try:
        answer = reasoner.generate_dhamma_answer(query, context, system_prompt)
        print("-" * 50)
        print(f"คำถาม: {query}")
        print("-" * 50)
        print(f"คำตอบจากนะโม:\n{answer}")
        print("-" * 50)
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    test_drive()
