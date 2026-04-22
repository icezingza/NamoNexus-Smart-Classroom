import google.generativeai as genai

def investigate_free_models():
    api_key = "AIzaSyBMuDg9jLpkY2ox8UQ7WIfmHNnGQdlkJDE"
    genai.configure(api_key=api_key)
    
    print("\n🔍 [นะโมสืบสวน] กำลังค้นหารุ่นโมเดลที่พี่ไอซ์ใช้ได้ฟรี...")
    try:
        models = genai.list_models()
        available_models = []
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                print(f"✅ พบรุ่น: {m.name}")
        
        if not available_models:
            print("❌ ไม่พบโมเดลที่รองรับการตอบคำถามเลยครับ")
        else:
            print(f"\n✨ รวมพบ {len(available_models)} รุ่นที่พี่ไอซ์มีสิทธิ์เรียกใช้ครับ")
            
    except Exception as e:
        print(f"🔥 เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

if __name__ == "__main__":
    investigate_free_models()
