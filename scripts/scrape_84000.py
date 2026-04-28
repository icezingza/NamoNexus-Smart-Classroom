# -*- coding: utf-8 -*-
"""
scrape_84000.py - ปฏิบัติการ "ล่าพระสูตร"
ดึงข้อมูลจาก 84000.org แบบคลีน HTML และแปลงเป็น JSON สำหรับเตรียมเข้า FAISS
"""

import urllib.request
import json
import time
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("กรุณาติดตั้ง BeautifulSoup ก่อนรัน: pip install beautifulsoup4")
    exit(1)


def scrape_sutta(book_num: int, item_start: int, item_end: int):
    url = f"https://84000.org/tipitaka/read/v.php?B={book_num}&A={item_start}&Z={item_end}&pagebreak=0"
    print(f"[*] กำลังสกัดข้อมูลจาก: {url}")

    # จำลองเป็น Browser ป้องกันการถูก Block
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req) as response:
            # 84000.org ใช้การเข้ารหัสภาษาไทยแบบ tis-620 / windows-874
            html_content = response.read().decode("tis-620", errors="ignore")
            soup = BeautifulSoup(html_content, "html.parser")

            # สกัดเนื้อหาแบบ No-HTML/No-CSS
            clean_text = soup.get_text(separator=" ", strip=True)

            return {
                "book": book_num,
                "item_start": item_start,
                "item_end": item_end,
                "content": clean_text,
                "source_url": url,
            }
    except Exception as e:
        print(f"[!] เกิดข้อผิดพลาด: {e}")
        return None


if __name__ == "__main__":
    # ทดสอบดึงพระสูตรเล่มที่ 9 (เริ่มที่ข้อ 1-100)
    result = scrape_sutta(book_num=9, item_start=1, item_end=100)

    if result:
        print("\n✅ สกัดข้อมูลสำเร็จ! ตัวอย่างเนื้อหา:")
        print(result["content"][:500] + "...\n")
