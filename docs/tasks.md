# Scheduler & Worker Tasks

สรุปสถานะคิวงาน ปัญหาที่ค้างอยู่ และกระบวนการ Background Tasks (Status as of May 24, 2026)

## 1. Current Sprints & Target
- **[ Phase 26 ] OpenClaw API Bridge:** ✅ สำเร็จแล้ว (Search routing, Dual-source RAG, Cloud Logging)
- **[ Phase 27 ] Multi-Channel Gateway:** 🔄 กำลังดำเนินการ 
  - เชื่อม Telegram Webhook
  - Redis Pub/Sub Sync จาก Teacher -> Display -> Telegram (< 500ms)
- **[ Phase 16 ] Namo-LoRA Fine-tuning:** 🔄 กำลังเตรียมการ 
  - เตรียมสภาพแวดล้อม WSL2 Ubuntu + CUDA
  - ใช้ `tools/lora/` เพื่อเทรนโมเดลภาษาไทย (`scb10x/llama-3-typhoon-v1.5-8b`)

## 2. Asynchronous Message Queues (Bull)
- เพื่อลดปัญหาคอขวดระหว่างการเชื่อมต่อแชทของ Telegram หากเกิดปริมาณมาก จะมีการส่งคำขอค้นหาข้อมูลเข้า **Search-Queue**
- ช่วยประวิงเวลาในการเรียก RAG + LLM และทำการตอบกลับภายหลังโดยที่ Telegram รับ Acknowledge ทันที

## 3. Server Watchdog & Monitoring
- **Watchdog Script (`scripts/namo_watchdog.ps1`):** ถูกฝังลงใน Windows Task Scheduler คอยเช็ค HTTP Health Check (`/health`) เป็นระยะ หากพบว่า Server หรือ Tunnel ร่วง ให้ทำการ restart ทันที
- **Cloud Logging:** ดูบันทึกใน GCP Logs Explorer (ผ่าน `bunyan` integration)
