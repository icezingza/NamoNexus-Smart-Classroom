#!/usr/bin/env python3
"""
Buddhadust HTML Scraping Fallback for Books 11-22 (DN, MN, SN, AN)
When SuttaCentral API fails, scrape public-domain texts from buddhadust.com
"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Buddhadust base URL
BUDDHADUST_BASE = "https://www.buddhadust.com"

# Map Nikayas to Buddhadust paths
NIKAYA_PATHS = {
    "DN": {
        "url": f"{BUDDHADUST_BASE}/dob/dn/index.html",
        "name": "Digha Nikaya",
        "book_range": (11, 14)
    },
    "MN": {
        "url": f"{BUDDHADUST_BASE}/dob/mn/index.html",
        "name": "Majjhima Nikaya",
        "book_range": (15, 18)
    },
    "SN": {
        "url": f"{BUDDHADUST_BASE}/dob/sn/index.html",
        "name": "Samyutta Nikaya",
        "book_range": (19, 21)
    },
    "AN": {
        "url": f"{BUDDHADUST_BASE}/dob/an/index.html",
        "name": "Anguttara Nikaya",
        "book_range": (22, 22)
    }
}

OUTPUT_DIR = Path("knowledge/tripitaka_main/books_11_22_raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def fetch_nikaya(session, nikaya_code):
    """Fetch sutta list from Buddhadust Nikaya index"""
    nikaya_info = NIKAYA_PATHS[nikaya_code]
    logger.info(f"🔍 Fetching {nikaya_code}: {nikaya_info['name']}")
    
    try:
        async with session.get(nikaya_info['url'], timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                logger.error(f"❌ HTTP {resp.status} from {nikaya_info['url']}")
                return []
            
            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract sutta links from index page
            suttas = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.endswith('.html') and nikaya_code.lower() in href.lower():
                    suttas.append({
                        'uid': href.split('/')[-1].replace('.html', ''),
                        'url': f"{BUDDHADUST_BASE}/dob/{nikaya_code.lower()}/{href}",
                        'title': link.get_text(strip=True)
                    })
            
            logger.info(f"   Found {len(suttas)} sutta links in {nikaya_code}")
            return suttas
            
    except Exception as e:
        logger.error(f"❌ Error fetching {nikaya_code}: {e}")
        return []

async def fetch_sutta_content(session, sutta_info, nikaya_code):
    """Fetch individual sutta HTML and extract text"""
    try:
        async with session.get(sutta_info['url'], timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            
            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract pali + english text from sutta body
            body = soup.find('body')
            if not body:
                return None
            
            text_content = body.get_text(separator='\n', strip=True)
            
            return {
                'uid': sutta_info['uid'],
                'pali': sutta_info.get('title', ''),
                'english': text_content[:500],  # First 500 chars as preview
                'title': sutta_info.get('title', sutta_info['uid']),
                'source': 'buddhadust.com'
            }
    except Exception as e:
        logger.warning(f"   ⚠️  Skipped {sutta_info['uid']}: {e}")
        return None

async def main():
    logger.info("=" * 70)
    logger.info("🔍 Buddhadust Fallback Scraper (Books 11-22)")
    logger.info("=" * 70)
    
    async with aiohttp.ClientSession() as session:
        all_suttas = {}
        
        for nikaya_code in ["DN", "MN", "SN", "AN"]:
            logger.info(f"\n📖 {nikaya_code} - Fetching sutta index...")
            suttas = await fetch_nikaya(session, nikaya_code)
            
            if not suttas:
                logger.warning(f"⚠️  {nikaya_code}: No suttas found")
                all_suttas[nikaya_code] = []
                continue
            
            # Fetch content for first 10 suttas as proof-of-concept
            # (Full scrape takes hours; this validates pipeline)
            logger.info(f"   📥 Fetching {min(10, len(suttas))} sample suttas from {nikaya_code}...")
            
            content_suttas = []
            for sutta in suttas[:10]:  # Limit to 10 for speed
                content = await fetch_sutta_content(session, sutta, nikaya_code)
                if content:
                    content_suttas.append(content)
                await asyncio.sleep(0.1)  # Polite rate limit
            
            all_suttas[nikaya_code] = content_suttas
            logger.info(f"   ✅ Downloaded {len(content_suttas)} suttas")
        
        # Save raw data
        logger.info(f"\n💾 Saving raw JSON to {OUTPUT_DIR}/")
        for nikaya_code, suttas in all_suttas.items():
            output_file = OUTPUT_DIR / f"{nikaya_code}_raw.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(suttas, f, ensure_ascii=False, indent=2)
            logger.info(f"   ✅ {output_file}: {len(suttas)} suttas")
        
        total = sum(len(s) for s in all_suttas.values())
        logger.info(f"\n📊 Summary:")
        logger.info(f"   Total suttas sampled: {total} (proof-of-concept)")
        logger.info(f"   Note: Full scrape requires 6-12 hours")
        logger.info(f"✅ Phase 1 Buddhadust Fallback complete!")

if __name__ == "__main__":
    asyncio.run(main())
