import httpx
from bs4 import BeautifulSoup
import re
import json
import time
import os
from pathlib import Path

# --- Configuration ---
START_BOOK = 23
END_BOOK = 45
ITEMS_PER_BOOK = 100  # ปรับเพิ่มจาก 20 เป็น 100 เพื่อความสมบูรณ์
BASE_URL = "https://84000.org/tipitaka/read/m_siri.php"
OUTPUT_DIR = Path("knowledge/global_library")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def deep_clean(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'form']):
        tag.decompose()
    
    # ดึงเฉพาะส่วนเนื้อหาหลัก
    raw_text = soup.get_text(separator='\n')
    
    lines = []
    found_start = False
    for line in raw_text.split('\n'):
        l = line.strip()
        if not l: continue
        
        # ค้นหาจุดเริ่มต้นที่แท้จริง
        if "มจร." in l or "พระไตรปิฎกเล่มที่" in l:
            found_start = True
        
        if not found_start: continue
        
        # จุดตัดจบ (Footer)
        if "ที่มา :" in l or "Compare with English" in l or "บันทึก" in l:
            break
            
        # กรอง Noise
        l = re.sub(r'\[\d+\]', '', l)
        l = re.sub(r'หน้า \d+', '', l)
        
        if len(l) > 2:
            lines.append(l)
            
    return '\n'.join(lines)

def start_global_hunt():
    print(f"🌟 นะโม 2 ปฏิบัติการกวาดล้างคลังปัญหาสากล (เล่ม {START_BOOK} ถึง {END_BOOK})")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with httpx.Client(headers=HEADERS, timeout=60.0) as client:
        for book_num in range(START_BOOK, END_BOOK + 1):
            book_data = []
            output_file = OUTPUT_DIR / f"book_{book_num}_clean.json"
            
            # ข้ามถ้ามีไฟล์อยู่แล้ว (ป้องกันการดึงซ้ำ)
            if output_file.exists():
                print(f"⏩ เล่ม {book_num} มีข้อมูลแล้ว ข้ามไปเล่มถัดไป...")
                continue
                
            print(f"\n🏔️ กำลังลุยเล่ม {book_num}...")
            
            for i in range(1, ITEMS_PER_BOOK + 1):
                try:
                    resp = client.get(BASE_URL, params={"B": book_num, "siri": i})
                    if resp.status_code == 200:
                        resp.encoding = 'cp874'
                        text = deep_clean(resp.text)
                        
                        if len(text) > 100:
                            # ป้องกันข้อมูลซ้ำซ้อนภายในเล่ม
                            if book_data and text[:100] == book_data[-1]['content'][:100]:
                                print(f"⚠️ [{i}] ข้อมูลซ้ำในเล่ม หยุดการดึงเล่มนี้", end='\r')
                                break
                                
                            entry = {
                                "book": book_num,
                                "item_id": i,
                                "title": text.split('\n')[0][:100],
                                "content": text,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            book_data.append(entry)
                            print(f"✅ [{i}] สกัดสำเร็จ ({len(text)} ตัวอักษร)", end='\r')
                        else:
                            # ถ้าเนื้อหาสั้นเกินไปติดต่อกัน อาจเป็นจุดจบของเล่ม
                            if i > 5: 
                                print(f"🏁 [{i}] ถึงจุดสิ้นสุดเนื้อหาเล่ม {book_num}", end='\r')
                                break
                    
                    time.sleep(1.0) # ถนอมเซิร์ฟเวอร์
                except Exception as e:
                    print(f"\n🔥 Error at Book {book_num} Item {i}: {e}")
                    time.sleep(5)
            
            if book_data:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(book_data, f, ensure_ascii=False, indent=2)
                print(f"\n💾 บันทึกเล่ม {book_num} เรียบร้อย! ({len(book_data)} รายการ)")

if __name__ == "__main__":
    start_global_hunt()
