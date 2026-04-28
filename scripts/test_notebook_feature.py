import requests
import json

BASE_URL = "http://localhost:8000"

def test_notebook_flow():
    # 1. จำลองแหล่งข้อมูล (Sources)
    sources = [
        {
            "title": "มงคลสูตร - ความกตัญญู",
            "text": "ความกตัญญู คือ การรู้คุณท่านที่ทำแล้วแก่ตน และการตอบแทนพระคุณนั้น ความกตัญญูเป็นเครื่องหมายของคนดี และเป็นมงคลอันสูงสุดข้อหนึ่ง",
            "source": "tripitaka"
        },
        {
            "title": "บันทึกเตรียมสอน - กิจกรรมเด็ก",
            "text": "ควรเน้นให้นักเรียนลองนึกถึงพระคุณของพ่อแม่ และเขียนการ์ดขอบคุณเล็กๆ ในห้องเรียน",
            "source": "teacher_notes"
        }
    ]

    print("\n--- [1] ทดสอบการสร้าง Briefing Doc ---")
    response = requests.post(f"{BASE_URL}/notebook/generate", json={
        "sources": sources,
        "mode": "briefing"
    })
    if response.status_code == 200:
        print(response.json().get("content")[:500] + "...")
    else:
        print(f"Error: {response.text}")

    print("\n--- [2] ทดสอบการสร้าง Audio Overview Script ---")
    response = requests.post(f"{BASE_URL}/notebook/generate", json={
        "sources": sources,
        "mode": "audio"
    })
    if response.status_code == 200:
        print(response.json().get("content")[:500] + "...")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    # หมายเหตุ: ระบบต้องรัน Backend (python -m namo_core.main) อยู่ถึงจะทดสอบได้
    print("เริ่มทดสอบระบบ Namo Notebook...")
    test_notebook_flow()
