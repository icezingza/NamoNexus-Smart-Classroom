import httpx
from bs4 import BeautifulSoup
import re
import json
import time
from pathlib import Path

# --- Configuration ---
BOOK_NUM = 25
BASE_URL = "https://84000.org/tipitaka/read/m_siri.php"
OUTPUT_FILE = Path("knowledge/tripitaka_v25_full.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def clean_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()
        
    # กวาดข้อความทั้งหน้า
    raw_text = soup.get_text(separator='\n')
    
    lines = []
    found_start = False
    for line in raw_text.split('\n'):
        l = line.strip()
        if not l: continue
        
        # จุดเริ่ม: มักจะเริ่มที่ "มจร." หรือชื่อเล่ม
        if "มจร." in l or "พระไตรปิฎกเล่มที่" in l:
            found_start = True
            
        if not found_start: continue
        
        # จุดจบ: ส่วนล่างของหน้า
        if "ที่มา :" in l or "Compare with English" in l:
            break
            
        # ลบเลขหน้า/บรรทัด
        l = re.sub(r'\[\d+\]', '', l)
        
        if len(l) > 2:
            lines.append(l)
            
    return '\n'.join(lines)

def run_production_hunt(start, end):
    print(f"🚀 นะโมเริ่มปฏิบัติการส่องข้อมูล เล่ม {BOOK_NUM} (ไอเทม {start}-{end})")
    
    all_data = []
    success_count = 0
    
    with httpx.Client(headers=HEADERS, timeout=30.0) as client:
        for i in range(start, end + 1):
            try:
                print(f"📥 ไอเทม {i}:", end=' ')
                resp = client.get(BASE_URL, params={"B": BOOK_NUM, "siri": i})
                if resp.status_code == 200:
                    resp.encoding = 'cp874'
                    text = clean_content(resp.text)
                    
                    print(f"[{text[:50]}...]", end=' ')
                    
                    if len(text) > 50:
                        # สกัดหัวข้อจริง
                        title_match = re.search(r'([๑-๙\d]+\..+)', text)
                        title = title_match.group(1) if title_match else f"ไอเทม {i}"
                        
                        entry = {
                            "item_id": i,
                            "title": f"เล่ม 25: {title.split('\n')[0]}",
                            "text": text,
                            "source": "84000.org (MCU)",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        all_data.append(entry)
                        success_count += 1
                        print(f"✅ สำเร็จ! ({len(text)} ตัวอักษร)")
                    else:
                        print("⚠️ เนื้อหาสั้นเกินไป ข้าม...")
                else:
                    print(f"❌ พลาด! (Status {resp.status_code})")
                
                # บันทึกความคืบหน้าทุกๆ 5 รายการ
                if success_count % 5 == 0 and success_count > 0:
                    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(all_data, f, ensure_ascii=False, indent=2)

                time.sleep(1.5)
                
            except Exception as e:
                print(f"🔥 Error: {e}")
                time.sleep(3)

    # บันทึกสรุปผล
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n✨ ภารกิจเสร็จสิ้น! ได้ทองคำปัญญามา {success_count} รายการ")

if __name__ == "__main__":
    # รัน Batch สุดท้าย: 151-250 เพื่อให้ครบเป้าหมาย (อิติวุตตกะ)
    run_production_hunt(151, 250)
