import json
import re

def repair_thai_encoding(file_path):
    print(f"🛠️ กำลังกู้ชีพภาษาไทยในไฟล์ {file_path}...")
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            
        # พยายามถอดรหัสจาก TIS-620 (รหัสภาษาไทยมาตรฐานเก่า)
        # เนื่องจากข้อมูลถูกเซฟเป็น UTF-8 แบบผิดๆ เราต้องแก้กลับ
        # ทดลองถอดรหัสแบบสุ่มเพื่อหาจุดที่ถูกต้อง
        content = raw_data.decode('utf-8')
        
        # กู้คืน: บางครั้งข้อมูลถูกอ่านเป็น latin-1 แล้วเซฟเป็น utf-8
        # เราต้องแปลงกลับเป็น bytes แบบ latin-1 แล้วถอดรหัสด้วย cp874 (Thai)
        data_json = json.loads(content)
        
        repaired_count = 0
        for item in data_json:
            original_text = item['text']
            try:
                # เทคนิคกู้ชีพ: latin1 -> bytes -> cp874
                repaired_text = original_text.encode('latin1').decode('cp874')
                item['text'] = repaired_text
                repaired_count += 1
            except:
                pass # ถ้าตัวไหนกู้ไม่ได้ให้ข้ามไปก่อน
                
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_json, f, ensure_ascii=False, indent=2)
            
        print(f"✅ กู้ชีพภาษาไทยสำเร็จ {repaired_count} รายการ!")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการกู้ชีพ: {e}")

if __name__ == "__main__":
    repair_thai_encoding('knowledge/tripitaka_v25_full.json')
