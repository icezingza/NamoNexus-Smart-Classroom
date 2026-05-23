# Coding Rules & Security

คู่มือระบุมาตรฐานการเขียนโค้ดและข้อตกลงเรื่องความปลอดภัยระดับ Sovereign Edition

## 1. Backend Integrity (100% Async)
- **Strictly Async:** ห้ามใช้คำสั่งแบบ Blocking I/O อย่าง `time.sleep()`, `requests.get()` ใน Endpoint, Scheduler หรือ Agent Runtimes โดยเด็ดขาด 
- **Solution:** ใช้ `asyncio.sleep()`, `httpx` หรือ `asyncio.to_thread` เสมอ

## 2. Port Standard
- Backend (FastAPI): **Port 8000**
- Frontend (Vite Local): **Port 5173**

## 3. Security Hardening & Zero-Secret
- **GCP Secret Manager:** `backend/namo_core/config/gcp_secrets.py` ทำหน้าที่ดึงข้อมูลที่สำคัญทั้งหมด ห้าม Hardcode Password, JWT Keys, หรือ API Keys ในโค้ด
- **.gitignore:** ไฟล์ `.env` ต้องอยู่ใน `.gitignore` ตลอดเวลา
- **Authentication:** ระบบจะยอมรับ Token ผ่าน `Authorization: Bearer` Header เท่านั้น (ไม่ยอมรับ Query Param เพื่อป้องกันความเสี่ยงที่ Token จะไปติดอยู่ใน URL Logs)
- **Rate Limit:** ล็อกพอร์ตหรือแบนผู้ใช้ชั่วคราวหากพยายามโจมตี (Limit 10 Requests / 60 seconds -> HTTP 429)

## 4. RAG Quality Constraint
- ก่อนทำการ Embeddings ทุกครั้ง ข้อมูลพระไตรปิฎกจะต้องผ่านกระบวนการ **Hard/Soft Quality Filter** เพื่อรับประกันความถูกต้อง ไม่บิดเบือน
