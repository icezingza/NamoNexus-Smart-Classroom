import httpx, sys, time
sys.path.insert(0, ".")

from namo_core.config.settings import get_settings
s = get_settings()

print(f"API Key : {s.reasoning_api_key[:12]}..." if s.reasoning_api_key else "API Key : NONE")
print(f"Base URL: {s.reasoning_api_base_url}")
print(f"Model   : {s.reasoning_model}")
print(f"Timeout : {s.reasoning_timeout_seconds}s")
print()
print("Testing Groq API... (please wait)")

t = time.time()
try:
    with httpx.Client(timeout=60) as c:
        r = c.post(
            f"{s.reasoning_api_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {s.reasoning_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": s.reasoning_model,
                "messages": [{"role": "user", "content": "ตอบว่า 'ระบบทำงานปกติ' เท่านั้น"}],
            },
        )
        elapsed = round(time.time() - t, 2)
        print(f"Status  : {r.status_code}  ({elapsed}s)")
        if r.status_code == 200:
            ans = r.json()["choices"][0]["message"]["content"]
            print(f"Answer  : {ans}")
            print("\n✅ Groq API ทำงานปกติ")
        else:
            print(f"Error   : {r.text[:400]}")
except Exception as e:
    elapsed = round(time.time() - t, 2)
    print(f"FAILED after {elapsed}s: {e}")
