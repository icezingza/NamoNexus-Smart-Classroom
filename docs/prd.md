# Product Journeys & Goals (PRD)

**NamoNexus Resonance Engine (NRE) v6.2.0 — Sovereign Edition**

## 1. วิสัยทัศน์ (Vision)
"Infrastructure แห่งปัญญา" ที่เปลี่ยนพระไตรปิฎกให้กลายเป็นระบบห้องเรียนธรรมะอัจฉริยะ (Smart Dhamma Classroom) ทำหน้าที่เป็นผู้ช่วยครูสอนธรรมะที่สามารถเข้าถึงข้อมูลพระไตรปิฎกได้อย่างแม่นยำ ลึกซึ้ง และรวดเร็ว

## 2. เสาหลัก S.M.A.R.T.
- **S - Sovereign:** อำนาจอธิปไตยดิจิทัล ควบคุมข้อมูลทั้งหมดบน Edge (Lenovo) + Cloud Run
- **M - Mastery:** เชี่ยวชาญระดับครู ผ่านการเรียนรู้คลังข้อมูลพระไตรปิฎก 171,357 Vectors
- **A - Async:** ฉับไว ไร้สะดุด ด้วยสถาปัตยกรรม Async 100% ตอบสนองด้วย Latency < 200ms
- **R - Resonance:** ค้นหาความหมายที่ตรงใจผ่าน Resonance Search และ Dual-source RAG
- **T - Truth:** ปลอดภัยขั้นสุด ไม่ผูกมัดค่าความลับ (Zero-Secret Policy) ด้วย GCP Secret Manager

## 3. Product Features & User Journey
### 3.1 สำหรับครูผู้สอน (Teacher Dashboard)
- ค้นหาข้อมูลธรรมะได้อย่างรวดเร็ว
- ควบคุมเนื้อหาที่จะแสดงขึ้นหน้าจอของนักเรียน (Dual-Screen Routing)

### 3.2 สำหรับนักเรียน (Student Display)
- หน้าจอรับข้อมูล (Display) แบบ Real-time ผ่าน WebSocket/Redis PubSub (Latency < 50ms)
- อ่านสรุปเนื้อหาธรรมะหรือรับฟังเสียงบรรยาย (Edge-TTS)

### 3.3 สำหรับสาธารณะชน (OpenClaw API & Gateway)
- เข้าถึงผ่าน Telegram Webhook (เช่น คุยกับ `@namo_bot`) และ Discord
- รอรับคำตอบธรรมะจากระบบภายใน < 3 วินาที

## 4. Market Position & Revenue Model
- **Freemium:** ถาม-ตอบฟรี 5 คำถามต่อวัน ผ่าน Telegram/Discord
- **Premium:** สมัครสมาชิกรายเดือน ($3-5) รับสิทธิ์ถามตอบไม่จำกัด
- **B2B / Academic:** สิทธิ์ใช้งาน API แบบ Bulk (เช่น 10k requests/เดือน) สำหรับมหาวิทยาลัยและองค์กรสงฆ์
