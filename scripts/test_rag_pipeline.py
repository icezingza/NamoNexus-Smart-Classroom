#!/usr/bin/env python3
"""
Namo Core - Interactive RAG Pipeline Tester
ใช้สำหรับทดสอบการค้นหา (FAISS) และการสร้างคำตอบ (LLM) แบบ End-to-End
"""

import httpx
import sys

API_URL = "http://127.0.0.1:8000"


def run_tester():
    print("==================================================")
    print("  🧘 NamoNexus RAG Pipeline Tester (Interactive)")
    print("  พิมพ์ 'exit' หรือ 'q' เพื่อออกจากการทดสอบ")
    print("==================================================")

    try:
        # เช็คว่า Server รันอยู่หรือไม่
        httpx.get(f"{API_URL}/health", timeout=5)
    except Exception:
        print("❌ ไม่สามารถเชื่อมต่อกับ Server ได้ กรุณารัน Backend ก่อน (port 8000)")
        return

    while True:
        try:
            query = input("\n🙏 คำถามถึงนะโม: ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                break

            print("🔍 [1/2] กำลังค้นหาข้อมูลจากพระไตรปิฎก (FAISS)...")
            ret_res = httpx.get(
                f"{API_URL}/knowledge/tripitaka/search",
                params={"q": query, "top_k": 3},
                timeout=10,
            )
            ret_data = ret_res.json()

            print("🧠 [2/2] กำลังวิเคราะห์และเรียบเรียงคำตอบ (LLM)...")
            chat_res = httpx.post(
                f"{API_URL}/nexus/text-chat",
                json={"text": query, "session_id": "TEST_RAG"},
                timeout=60,
            )
            chat_data = chat_res.json()

            print("\n" + "=" * 50)
            print("📚 ข้อมูลอ้างอิงที่ค้นพบ (Top 3):")
            for i, doc in enumerate(ret_data.get("results", [])):
                score = doc.get("score", 0)
                title = doc.get("title", "ไม่ระบุ")
                print(f"  {i + 1}. {title} (ความแม่นยำ: {score:.2f})")

            print("-" * 50)
            print("💬 คำตอบจากนะโม:")
            reasoning = chat_data.get("reasoning", {})
            answer = reasoning.get("answer", "ไม่มีคำตอบจากระบบ")
            print(answer)
            print("=" * 50)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ เกิดข้อผิดพลาด: {e}")


if __name__ == "__main__":
    run_tester()
