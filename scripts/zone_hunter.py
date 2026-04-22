import httpx
from bs4 import BeautifulSoup
import re
import json
import time
from pathlib import Path

# --- Configuration for Global Hunter ---
BASE_URL = "https://84000.org/tipitaka/read/m_siri.php"
OUTPUT_DIR = Path("knowledge/new_zone")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def clean_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()
    raw_text = soup.get_text(separator='\n')
    lines = []
    found_start = False
    for line in raw_text.split('\n'):
        l = line.strip()
        if not l: continue
        if "มจร." in l or "พระไตรปิฎกเล่มที่" in l:
            found_start = True
        if not found_start: continue
        if "ที่มา :" in l or "Compare with English" in l:
            break
        l = re.sub(r'\[\d+\]', '', l)
        if len(l) > 2:
            lines.append(l)
    return '\n'.join(lines)

def hunt_book(book_num, items_count=20):
    print(f"\n🏔️ กำลังเข้าสู่เขตเล่มที่ {book_num}...")
    book_data = []
    
    with httpx.Client(headers=HEADERS, timeout=30.0) as client:
        for i in range(1, items_count + 1):
            try:
                resp = client.get(BASE_URL, params={"B": book_num, "siri": i})
                if resp.status_code == 200:
                    resp.encoding = 'cp874'
                    text = clean_content(resp.text)
                    if len(text) > 100:
                        entry = {
                            "book": book_num,
                            "item_id": i,
                            "title": text.split('\n')[0],
                            "content": text
                        }
                        book_data.append(entry)
                        print(f"✅ เล่ม {book_num} [{i}] สกัดสำเร็จ", end='\r')
                    else:
                        print(f"⚠️ เล่ม {book_num} [{i}] เนื้อหาสั้นเกินไป", end='\r')
                time.sleep(1.2) # ถนอมเซิร์ฟเวอร์
            except Exception as e:
                print(f"\n🔥 Error at Book {book_num} Item {i}: {e}")
                time.sleep(2)
    
    if book_data:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / f"book_{book_num}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(book_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 บันทึกเล่ม {book_num} เรียบร้อย! ({len(book_data)} รายการ)")

if __name__ == "__main__":
    # ปฏิบัติการกวาดล้างยาวจาก 23 จนถึง 45 (สุ่มเก็บเล่มละ 20 รายการเพื่อความรวดเร็วและครอบคลุม)
    books_to_hunt = [24] + list(range(28, 46))
    print(f"🚀 เริ่มปฏิบัติการ Long Hunt ครอบคลุม {len(books_to_hunt)} เล่ม...")
    
    for book in books_to_hunt:
        hunt_book(book, items_count=20)
    
    print("\n✨ ภารกิจ Long Hunt สำเร็จลุล่วง! คลังความรู้ 23-45 พร้อมประจำการแล้วครับ")
