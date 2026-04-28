import httpx
from bs4 import BeautifulSoup
import re
import json
import time

def quick_test():
    base_url = "https://84000.org/tipitaka/read/m_siri.php"
    items = [1, 21, 41]
    results = {}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    with httpx.Client(headers=headers, timeout=30.0) as client:
        for i in items:
            print(f"Testing siri={i}...")
            resp = client.get(base_url, params={"B": 25, "siri": i})
            print(f"Status: {resp.status_code}, Length: {len(resp.content)}")
            resp.encoding = 'cp874'
            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text()
            results[i] = text.strip()[:200].replace('\n', ' ')
            time.sleep(2)
            
    for i, res in results.items():
        print(f"\n--- Item A={i} ---")
        print(res)

if __name__ == "__main__":
    quick_test()
