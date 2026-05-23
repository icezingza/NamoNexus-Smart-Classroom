# Subsystem Topologies (Architecture)

**Version:** NRE v6.2.0 Cloud Run Edition

## 1. Hybrid Architecture (Edge + Cloud)

```text
[ Teacher Tablet ]      [ Student Display ]      [ Telegram/Discord Users ]
       ↓                        ↑                           ↑
[ www.namonexus.com ] ← (WebSocket wss://)       [ OpenClaw API Gateway ]
       ↓                                                    ↓
[ Cloudflare Tunnel / api.namonexus.com (Cloud Run) ] <─────┘
       ↓
[ Backend: FastAPI (Async 100%) ]
  ├── Redis (State/PubSub)
  ├── PostgreSQL (Cloud SQL via Alembic)
  └── FAISS — Tripitaka (171,357 vectors) + Global Library (23 books)
```

## 2. Core Subsystems

### 2.1 The Wisdom Stream (Backend)
- 100% Async I/O (ใช้ `asyncio.to_thread` และ `aiofiles`)
- **Port:** `8000` (Local/Edge), Cloud Run จัดการเรื่อง Port และการ Scale แบบอัตโนมัติ
- **Database:** PostgreSQL (Cloud SQL) สำหรับ Production, SQLite สำหรับ Local Dev

### 2.2 The OpenClaw Gateway (API Bridge)
- รองรับ POST `/api/search` และเชื่อมกับ Smart Classroom
- จัดการ JWT Authorization, การทำ Connection Pooling, และ Exponential Backoff (3 retries)
- รองรับ Trace ID Propagation เพื่อการตามรอย Log จากระบบภายนอกเข้ามาที่ Backend
- **Gateway Endpoints:** `/telegram` และ `/discord` สำหรับ Webhook

### 2.3 Security Hardening
- **Secrets:** อ่านค่าความลับจาก **GCP Secret Manager** เท่านั้น (ห้าม Hardcode)
- **Auth:** รับ Token ผ่าน `Authorization: Bearer` Header เท่านั้น 
- **Rate Limit:** จำกัด 10 failed attempts ต่อ 60 วินาที

### 2.4 Cloud Observability
- ใช้ **Bunyan** คู่กับ **Cloud Logging** สำหรับทำ Structured JSON Logging
- มี Log ครอบคลุม: `trace_id`, `operation`, `user_id`, `latency_ms`, `status`
