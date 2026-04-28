import httpx
from bs4 import BeautifulSoup
import re
import json
import time
from pathlib import Path

# --- Configuration ---
BASE_URL = "https://84000.org/tipitaka/read/m_siri.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def deep_clean(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'form']):
        tag.decompose()
    
    raw_text = soup.get_text(separator='\n')
    lines = []
    found_start = False
    for line in raw_text.split('\n'):
        l = line.strip()
        if not l: continue
        
        # จุดเริ่มที่แท้จริง
        if "มจร." in l or "พระไตรปิฎกเล่มที่" in l:
            found_start = True
        if not found_start: continue
        
        # จุดตัดจบ
        if "ที่มา :" in l or "Compare with English" in l or "บันทึก" in l:
            break
            
        # ลบ Noise
        l = re.sub(r'\[\d+\]', '', l)
        l = re.sub(r'หน้า \d+', '', l)
        
        if len(l) > 2:
            lines.append(l)
            
    return '\n'.join(lines)

def run_deep_hunt(book_num, items_limit=500):
    print(f"\n🏔️ [นะโม 1] เริ่มปฏิบัติการเจาะลึก เล่มที่ {book_num}...")
    output_dir = Path("knowledge/full_tripitaka/consolidated")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"book_{book_num:02d}_deep.json"
    
    book_data = []
    consecutive_skips = 0
    max_skips = 10 # ถ้าเจอหน้าว่างหรือหน้าซ้ำติดกัน 10 หน้า ถึงจะหยุด (แปลว่าจบเล่มจริง)
    
    with httpx.Client(headers=HEADERS, timeout=60.0) as client:
        for i in range(1, items_limit + 1):
            try:
                resp = client.get(BASE_URL, params={"B": book_num, "siri": i})
                if resp.status_code == 200:
                    resp.encoding = 'cp874'
                    text = deep_clean(resp.text)
                    
                    # ตรวจสอบความซ้ำซ้อนแบบละเอียด (เช็ค 500 ตัวแรก)
                    is_duplicate = False
                    if book_data:
                        # เทียบกับรายการก่อนหน้า
                        if text[:500] == book_data[-1]['content'][:500]:
                            is_duplicate = True
                    
                    if len(text) > 200 and not is_duplicate:
                        entry = {
                            "book": book_num,
                            "item_id": i,
                            "title": text.split('\n')[0][:150],
                            "content": text,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        book_data.append(entry)
                        consecutive_skips = 0
                        print(f"✅ [{i}] สกัดสำเร็จ ({len(text)} ตัวอักษร)", end='\r')
                    else:
                        consecutive_skips += 1
                        reason = "ซ้ำ" if is_duplicate else "สั้นเกินไป"
                        print(f"⏭️ [{i}] ข้าม ({reason})", end='\r')
                        
                    if consecutive_skips >= max_skips:
                        print(f"\n🏁 ถึงจุดสิ้นสุดเล่ม {book_num} ที่รายการ {i} (พบหน้าว่าง/ซ้ำติดกัน {max_skips} หน้า)")
                        break
                
                # หน่วงเวลานิดนึงเพื่อความสุภาพต่อเซิร์ฟเวอร์
                time.sleep(0.8)
                
            except Exception as e:
                print(f"\n🔥 Error at Item {i}: {e}")
                time.sleep(5)
                
    if book_data:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(book_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 บันทึกเล่ม {book_num} สำเร็จ! ได้มา {len(book_data)} รายการคุณภาพ")
    else:
        print(f"\n❌ ไม่พบข้อมูลในเล่ม {book_num}")

if __name__ == "__main__":
    # เริ่มทดสอบกับเล่ม 2 (พระวินัยปิฎก มหาวิภังค์ ภาค 2)
    run_deep_hunt(2)
