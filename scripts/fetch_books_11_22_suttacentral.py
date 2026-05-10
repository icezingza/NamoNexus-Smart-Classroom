#!/usr/bin/env python3
"""
Fetch Books 11-22 from SuttaCentral API
Requires: aiohttp, tqdm
Run: python3 scripts/fetch_books_11_22_suttacentral.py
"""
import json
import asyncio
from pathlib import Path
import sys

# Try import, give user helpful message if missing
try:
    import aiohttp
except ImportError:
    print("❌ Missing aiohttp. Install: pip install aiohttp")
    sys.exit(1)

SC_API = "https://api.suttacentral.net"
NIKAYAS = {
    "DN": (11, 14, "Digha Nikaya"),
    "MN": (15, 18, "Majjhima Nikaya"),
    "SN": (19, 21, "Samyutta Nikaya"),
    "AN": (22, 22, "Anguttara Nikaya"),
}

async def fetch_sutta(session, uid, pali_author="ms", en_author="sujato"):
    """Fetch single sutta in Pali + English"""
    try:
        async with session.get(f"{SC_API}/texts/{uid}/pli/{pali_author}", timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return None
            pali_data = await r.json()
        
        async with session.get(f"{SC_API}/texts/{uid}/en/{en_author}", timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                en_text = "[English translation unavailable]"
            else:
                en_data = await r.json()
                en_text = en_data.get("text", "")
        
        return {
            "uid": uid,
            "pali": pali_data.get("text", ""),
            "english": en_text,
            "title": pali_data.get("title", ""),
        }
    except Exception as e:
        print(f"⚠️  {uid}: {str(e)}")
        return None

async def fetch_nikaya(nikaya_abbr):
    """Fetch all suttas in a Nikaya"""
    try:
        endpoint = f"{SC_API}/suttaplex/{nikaya_abbr}"
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    print(f"❌ {nikaya_abbr}: HTTP {r.status}")
                    return []
                collection = await r.json()
            
            suttas = []
            items = collection.get("items", [])
            print(f"\n📥 Fetching {nikaya_abbr}: {len(items)} suttas")
            
            for i, item in enumerate(items):
                sutta = await fetch_sutta(session, item["uid"])
                if sutta:
                    suttas.append(sutta)
                if (i + 1) % 10 == 0:
                    print(f"   Progress: {i+1}/{len(items)}")
            
            return suttas
    except Exception as e:
        print(f"❌ Error fetching {nikaya_abbr}: {str(e)}")
        return []

async def main():
    out_dir = Path("knowledge/tripitaka_main/books_11_22_raw")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔍 SuttaCentral Phase 1 Verification & Download")
    print("=" * 70)
    
    total_suttas = 0
    for nikaya, (start_book, end_book, name) in NIKAYAS.items():
        suttas = await fetch_nikaya(nikaya)
        total_suttas += len(suttas)
        
        if suttas:
            out_file = out_dir / f"{nikaya}_raw.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(suttas, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(suttas)} suttas → {out_file}")
        else:
            print(f"⚠️  {nikaya}: No suttas downloaded")
    
    print(f"\n📊 Summary:")
    print(f"   Total suttas downloaded: {total_suttas}")
    print(f"   Expected chunks (600 chars): ~{total_suttas * 8}")
    print(f"\n✅ Phase 1 Verification complete!")

if __name__ == "__main__":
    asyncio.run(main())
