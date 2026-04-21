"""ทดสอบ NamoNexus Loop endpoint: POST /nexus/voice-chat?speak=true

การใช้งาน:
  python test_nexus.py                    # ใช้ dummy WAV ที่สร้างอัตโนมัติ
  python test_nexus.py path/to/audio.wav  # ใช้ไฟล์เสียงจริง
  python test_nexus.py --no-speak         # ปิด TTS (speak=false)
"""

import io
import json
import struct
import sys
import wave

# Force UTF-8 output on Windows (แก้ UnicodeEncodeError ใน terminal cp874)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import requests

BASE_URL = "http://127.0.0.1:8000"
ENDPOINT = f"{BASE_URL}/nexus/voice-chat"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: สร้าง WAV ขนาดเล็ก (1 วินาที silence) สำหรับทดสอบเมื่อไม่มีไฟล์จริง
# ─────────────────────────────────────────────────────────────────────────────

def _make_dummy_wav(duration_sec: float = 1.0, sample_rate: int = 16_000) -> bytes:
    """สร้างไฟล์ WAV PCM16 mono ที่เป็น silence สำหรับ smoke-test."""
    n_samples = int(sample_rate * duration_sec)
    pcm_data = struct.pack(f"<{n_samples}h", *([0] * n_samples))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)       # mono
        wf.setsampwidth(2)       # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)

    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: พิมพ์ผลลัพธ์อย่างสวยงาม
# ─────────────────────────────────────────────────────────────────────────────

def _print_section(title: str, data) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)
    if data is None:
        print("  (ไม่มีข้อมูล / None)")
        return
    if isinstance(data, dict):
        for key, value in data.items():
            # ตัด audio_base64 ให้สั้นลงเพื่อไม่ท่วม terminal
            if key == "audio_base64" and isinstance(value, str) and len(value) > 80:
                print(f"  {key}: {value[:40]}...{value[-10:]}  [{len(value)} chars]")
            elif isinstance(value, (dict, list)):
                print(f"  {key}:")
                print(f"    {json.dumps(value, ensure_ascii=False, indent=2)}")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"  {data}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── Parse args ─────────────────────────────────────────────────────────────
    args = sys.argv[1:]
    speak = True
    audio_path: str | None = None

    for arg in args:
        if arg == "--no-speak":
            speak = False
        elif not arg.startswith("--"):
            audio_path = arg

    # ── Load audio ─────────────────────────────────────────────────────────────
    if audio_path:
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            filename = audio_path.split("/")[-1].split("\\")[-1]
            print(f"[+] ใช้ไฟล์เสียง: {audio_path}  ({len(audio_bytes):,} bytes)")
        except FileNotFoundError:
            print(f"[!] ไม่พบไฟล์: {audio_path}")
            sys.exit(1)
    else:
        audio_bytes = _make_dummy_wav()
        filename = "dummy_silence.wav"
        print(f"[+] สร้าง dummy WAV (1 วินาที silence, 16kHz mono)  ({len(audio_bytes):,} bytes)")

    # ── Send request ───────────────────────────────────────────────────────────
    url = f"{ENDPOINT}?speak={str(speak).lower()}"
    print(f"[+] POST {url}")

    try:
        response = requests.post(
            url,
            files={"audio": (filename, audio_bytes, "audio/wav")},
            timeout=60,
        )
    except requests.exceptions.ConnectionError:
        print(f"\n[!] เชื่อมต่อไม่ได้ — ตรวจสอบว่า server รันอยู่ที่ {BASE_URL}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\n[!] Request timeout (60s) — server อาจกำลังโหลด Whisper model")
        sys.exit(1)

    print(f"[+] HTTP Status: {response.status_code}")

    # ── Parse response ─────────────────────────────────────────────────────────
    if response.status_code != 200:
        print(f"\n[!] Error response:\n{response.text}")
        sys.exit(1)

    try:
        data = response.json()
    except ValueError:
        print(f"\n[!] ไม่สามารถ parse JSON:\n{response.text[:500]}")
        sys.exit(1)

    # ── Print results ──────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  ผลลัพธ์ NamoNexus Voice Chat")
    print("═" * 60)

    _print_section("TRANSCRIPT  (ผลการถอดเสียง)", data.get("transcript"))
    _print_section("REASONING   (คำตอบจาก LLM + RAG)", data.get("reasoning"))
    _print_section("TTS         (ผลการสังเคราะห์เสียง)", data.get("tts"))
    _print_section("PIPELINE META", data.get("pipeline_meta"))

    print("\n" + "═" * 60)

    # สรุปสั้นๆ
    transcript_text = (data.get("transcript") or {}).get("text", "")
    reasoning_answer = (data.get("reasoning") or {}).get("answer", "")
    print("\n[สรุป]")
    print(f"  transcript : {transcript_text!r}")
    print(f"  reasoning  : {reasoning_answer[:200]!r}{'...' if len(reasoning_answer) > 200 else ''}")
    print()


if __name__ == "__main__":
    main()
