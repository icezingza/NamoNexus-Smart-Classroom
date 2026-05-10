# -*- coding: utf-8 -*-
"""
scrape_84000.py - ปฏิบัติการ "ล่าพระสูตร" (Async Edition)
ดึงข้อมูลจาก 84000.org แบบคลีน HTML และแปลงเป็น JSON สำหรับเตรียมเข้า FAISS
"""

import asyncio
import httpx
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("กรุณาติดตั้ง BeautifulSoup ก่อนรัน: pip install beautifulsoup4")
    exit(1)

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# จำกัดจำนวนการเชื่อมต่อพร้อมกันไม่ให้โดน Block
MAX_CONCURRENT_REQUESTS = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

async def scrape_sutta(client: httpx.AsyncClient, book_num: int, item_start: int, item_end: int) -> Optional[Dict]:
    url = f"https://84000.org/tipitaka/read/v.php?B={book_num}&A={item_start}&Z={item_end}&pagebreak=0"
    
    async with semaphore:
        try:
            logger.info(f"[*] กำลังสกัดข้อมูลจาก: {url}")
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            
            # 84000.org ใช้การเข้ารหัสภาษาไทยแบบ tis-620 / windows-874
            html_content = response.content.decode("tis-620", errors="ignore")
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
            logger.error(f"[!] เกิดข้อผิดพลาดที่ {url}: {e}")
            return None

async def main():
    # ทดสอบดึงพระสูตรเล่มที่ 9 (เริ่มที่ข้อ 1-100)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        result = await scrape_sutta(client, book_num=9, item_start=1, item_end=100)

        if result:
            print("\n✅ สกัดข้อมูลสำเร็จ! ตัวอย่างเนื้อหา:")
            print(result["content"][:500] + "...\n")

if __name__ == "__main__":
    asyncio.run(main())
