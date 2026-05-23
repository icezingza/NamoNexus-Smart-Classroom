# UX/UI & Streaming Components

## 1. แนวทางการออกแบบ Frontend
- **Framework:** React 18 + Vite + TypeScript
- **Styling:** Tailwind CSS + Shadcn UI
- **Routing:** ระบบ Dual-Screen
  - `/teacher` สำหรับให้ครูผู้สอนควบคุมเนื้อหา
  - `/display` สำหรับแสดงผลให้นักเรียนดู

## 2. Streaming & Real-Time Sync
ระบบนี้ให้ความสำคัญกับความเร็ว (Real-time Experience) เพื่อป้องกันหน้าจอค้างและเพื่อให้ครูสามารถมีปฏิสัมพันธ์กับนักเรียนได้อย่างลื่นไหล

### 2.1 WebSocket Connection
- **Protocol:** `wss://` ผ่าน Cloudflare Tunnel
- **Heartbeat:** 30 วินาที Ping เพื่อป้องกันการหลุด (Auto-reconnect)
- **Latency Target:** < 50ms ระหว่างจอ Teacher และ Display

### 2.2 Redis Pub/Sub
- ทำหน้าที่เป็น Event Bus หลัก
- Channel `namo:updates`: กระจายผลลัพธ์คำถาม-คำตอบ (Dhamma query results) ให้กับทุก Client ที่กำลังเชื่อมต่อ รวมถึง Telegram Gateway

### 2.3 UI Interaction Rules
- **No Blocking Loading:** ระหว่างที่รอ RAG หรือรอโมเดลคิด ห้ามล็อคหน้าจอทั้งหมด ต้องมี Micro-animations แจ้งเตือนสถานะ
- **Touch-Friendly:** หน้าต่างของ `/teacher` ต้องถูกออกแบบมาสำหรับการใช้งานบน Tablet (Tablet-First Design)
