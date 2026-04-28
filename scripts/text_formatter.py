import json
import re
from pathlib import Path

INPUT_FILE = Path("knowledge/tripitaka_v25_full.json")
OUTPUT_FILE = Path("knowledge/tripitaka_v25_distributed.json")

def distill_wisdom():
    print(f"🧹 กำลังกลั่นกรองความรู้จาก {INPUT_FILE}...")
    
    if not INPUT_FILE.exists():
        print("❌ ไม่พบไฟล์ต้นทางครับ!")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    distilled_data = []
    
    # คำที่ต้องการตัดออก (UI Noise)
    noise_patterns = [
        r"บทนำ", r"พระวินัยปิฎก", r"พระสุตตันตปิฎก", r"พระอภิธรรมปิฎก",
        r"ค้นพระไตรปิฎก", r"ชาดก", r"หนังสือธรรมะ", r"Select English version",
        r"metta :", r"accesstoinsight", r"suttacentral", r"ฉบับหลวง",
        r"ฉบับมหาจุฬาฯ", r"บาลีอักษรไทย", r"PaliRoman", r"ตัวอักษรขนาด",
        r"พระไตรปิฎกเล่มที่ ๒๕", r"\[ฉบับมหาจุฬาฯ\]", r"ขุททกนิกาย",
        r"มจร\.", r"_____________"
    ]
    
    for item in data:
        text = item['text']
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            l = line.strip()
            # ข้ามบรรทัดที่เป็น Noise
            is_noise = any(re.search(pattern, l, re.IGNORECASE) for pattern in noise_patterns)
            if is_noise:
                continue
            if len(l) < 2:
                continue
            clean_lines.append(l)
            
        distilled_text = '\n'.join(clean_lines)
        
        if len(distilled_text) > 50:
            distilled_data.append({
                "id": item['item_id'],
                "title": item['title'].replace("เล่ม 25: ", ""),
                "content": distilled_text,
                "category": "Khuddaka Nikaya"
            })

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(distilled_data, f, ensure_ascii=False, indent=2)
    
    print(f"✨ กลั่นกรองสำเร็จ! {len(distilled_data)} รายการ พร้อมใช้งานใน {OUTPUT_FILE}")

if __name__ == "__main__":
    distill_wisdom()
