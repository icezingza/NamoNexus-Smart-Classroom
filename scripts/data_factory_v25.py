import httpx
from bs4 import BeautifulSoup
import re
import json
import time
from pathlib import Path

# --- Configuration ---
BOOK_NUM = 25
# ใช้หน้า m_siri.php ซึ่งดึงง่ายและคลีนกว่า
BASE_URL = "https://84000.org/tipitaka/read/m_siri.php"
OUTPUT_FILE = Path("knowledge/tripitaka_v25_clean.json")
DELAY = 1.5

def clean_text(text):
    # ลบเลขหน้า เลขบรรทัด และขยะ
    text = re.sub(r'\[\d+\]', '', text)
    text = text.replace('\xa0', ' ')
    text = re.sub(r' +', ' ', text)
    return text.strip()

def scrape_volume_25():
    print(f"🚀 ปฏิบัติการ Data Factory: เล่ม {BOOK_NUM} (ฉบับมหาจุฬา/สยามรัฐ)")
    all_chunks = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    # ทดลองดึง 10 ไอเทมแรก (ไอเทมใน m_siri มักจะเป็นช่วงๆ)
    for item in range(1, 11):
        params = {"B": BOOK_NUM, "A": item}
        print(f"📥 กำลังดึงไอเทมที่ {item}...")
        
        try:
            with httpx.Client(headers=headers, timeout=30.0) as client:
                resp = client.get(BASE_URL, params=params)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # ใน m_siri เนื้อหามักจะอยู่ในช่องตรงกลางที่มีสีกรอบ
                # เราจะกวาดเนื้อหาที่เป็นตัวอักษรทั้งหมดในส่วนกลาง
                content_div = soup.find('table', {'width': '90%'}) or soup.find('font', {'color': 'black'})
                
                if content_div:
                    raw_text = content_div.get_text()
                    # แบ่งเนื้อหาเป็นส่วนๆ
                    clean_content = clean_text(raw_text)
                    if len(clean_content) > 100:
                        all_chunks.append({
                            "chunk_id": f"v25_item_{item}",
                            "title": f"พระไตรปิฎก เล่มที่ {BOOK_NUM} (ไอเทม {item})",
                            "text": clean_content,
                            "source_url": str(resp.url)
                        })
                        print(f"✅ ดึงสำเร็จ! (ขนาด {len(clean_content)} ตัวอักษร)")
                
            time.sleep(DELAY)
            
        except Exception as e:
            print(f"❌ พลาดที่ไอเทม {item}: {e}")

    # บันทึกไฟล์
    if all_chunks:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        print(f"\n✨ สำเร็จ! บันทึกข้อมูล {len(all_chunks)} รายการลงใน {OUTPUT_FILE}")
    else:
        print("\n❌ ยังดึงไม่ได้เลยครับคุณครู...")

if __name__ == "__main__":
    scrape_volume_25()
