# PostgreSQL Migration Runbook — NamoNexus

ย้าย NamoNexus จาก SQLite (local dev) → Cloud SQL PostgreSQL (production)

---

## 1. สร้าง Cloud SQL Instance

```bash
# ตั้งค่าตัวแปร
PROJECT_ID="your-gcp-project-id"
INSTANCE_NAME="namo-classroom-db"
REGION="asia-southeast1"          # ใกล้ที่สุดกับ server
DB_NAME="namo_classroom"
DB_USER="namo_app"

# สร้าง Cloud SQL PostgreSQL 15
gcloud sql instances create $INSTANCE_NAME \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-auto-increase \
  --backup-start-time=02:00

# สร้าง database และ user
gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME
gcloud sql users create $DB_USER \
  --instance=$INSTANCE_NAME \
  --password="<strong-password-here>"
```

---

## 2. เตรียม .env สำหรับ Production

เปิด `backend/namo_core/.env` แก้ไขส่วนต่อไปนี้:

```dotenv
# --- Database ---
# SQLite (dev):
# NAMO_DATABASE_URL=sqlite:///./namo_classroom.db

# Cloud SQL via Unix socket (production — ใช้กับ Cloud Run):
NAMO_DATABASE_URL=postgresql+psycopg2://namo_app:<password>@/namo_classroom?host=/cloudsql/<PROJECT_ID>:<REGION>:<INSTANCE_NAME>

# Cloud SQL via TCP (ใช้กับ local test ผ่าน Cloud SQL Auth Proxy):
# NAMO_DATABASE_URL=postgresql+psycopg2://namo_app:<password>@127.0.0.1:5432/namo_classroom

# --- Security ---
NAMO_JWT_SECRET_KEY=<random-32-chars-minimum>
NAMO_ENV=production

# --- Admin password (bcrypt hash) ---
# สร้าง hash ด้วยคำสั่งด้านล่าง แล้ว paste ค่า hash ตรงนี้:
NAMO_ADMIN_PASSWORD=$2b$12$<hash-value-here>
```

### สร้าง bcrypt hash สำหรับ admin password

```bash
python3 -c "
import bcrypt, getpass
pw = getpass.getpass('New admin password: ')
h  = bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12))
print('Hash:', h.decode())
"
```

คัดลอก hash (บรรทัดที่ขึ้นต้นด้วย `$2b$12$`) ใส่ใน `NAMO_ADMIN_PASSWORD`

---

## 3. ติดตั้ง Dependencies

```bash
cd backend/namo_core
pip install -r requirements.txt   # รวม alembic>=1.13.0 แล้ว
```

---

## 4. Apply Migrations

```bash
cd backend/namo_core

# ดู migration ปัจจุบัน (ควรเป็น None ในครั้งแรก)
alembic current

# Apply ทุก migration จนถึง HEAD
alembic upgrade head

# ตรวจสอบว่า apply สำเร็จ
alembic current    # ควรแสดง: 0001 (head)
```

### ดู SQL ก่อน apply (dry-run)

```bash
alembic upgrade head --sql 2>/dev/null | head -100
```

---

## 5. ตรวจสอบตารางใน PostgreSQL

```bash
# ผ่าน Cloud SQL Auth Proxy หรือ gcloud sql connect
psql -U namo_app -d namo_classroom -c "\dt"
```

ควรเห็น 10 ตาราง:
```
 teachers
 classroom_sessions
 event_logs
 notebooks
 notebook_sources
 notebook_contents
 notebook_jobs
 notebook_audit_logs
 semantic_cache_entries
 ai_feedback
 alembic_version       ← Alembic tracking table (สร้างอัตโนมัติ)
```

---

## 6. Deploy ใน Cloud Run

### Dockerfile snippet (ตรวจสอบว่ามี Cloud SQL connector)

```dockerfile
# เพิ่ม Cloud SQL Python Connector ถ้าใช้ IAM auth แทน password
RUN pip install cloud-sql-python-connector[pg8000]
```

### Cloud Run env vars ที่ต้องตั้ง

| Variable | ค่า |
|---|---|
| `NAMO_DATABASE_URL` | `postgresql+psycopg2://namo_app:<pw>@/namo_classroom?host=/cloudsql/<conn>` |
| `NAMO_JWT_SECRET_KEY` | JWT secret (≥ 32 chars) |
| `NAMO_ADMIN_PASSWORD` | bcrypt hash |
| `NAMO_ADMIN_USERNAME` | `admin` (หรือชื่อที่ต้องการ) |
| `NAMO_ENV` | `production` |
| `NAMO_REDIS_URL` | `redis://<host>:6379/0` |

### Cloud Run connection name

```bash
gcloud run deploy namo-backend \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:$INSTANCE_NAME \
  ...
```

---

## 7. Run Migrations ใน Cloud Run (one-shot job)

```bash
gcloud run jobs create namo-migrate \
  --image=gcr.io/$PROJECT_ID/namo-backend:latest \
  --command="alembic" \
  --args="upgrade,head" \
  --set-env-vars="NAMO_DATABASE_URL=...,NAMO_ENV=production" \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:$INSTANCE_NAME \
  --region=$REGION

gcloud run jobs execute namo-migrate --region=$REGION --wait
```

---

## 8. Generate migration หลังเพิ่ม/แก้ Model

```bash
cd backend/namo_core
alembic revision --autogenerate -m "add_column_xyz_to_teachers"
# ตรวจสอบไฟล์ที่สร้างใน migrations/versions/ ก่อน apply เสมอ
alembic upgrade head
```

---

## 9. Rollback

```bash
# ถอย 1 migration
alembic downgrade -1

# ถอยไปถึง revision ที่ระบุ
alembic downgrade 0001

# ถอยทั้งหมด (ลบทุกตาราง)
alembic downgrade base
```

---

## 10. Data Migration จาก SQLite (ถ้ามี data อยู่แล้ว)

```bash
# Export จาก SQLite
sqlite3 namo_classroom.db .dump > sqlite_dump.sql

# แปลงด้วย pgloader (tool ฟรี)
pgloader sqlite:///./namo_classroom.db \
         postgresql://namo_app:<pw>@127.0.0.1/namo_classroom

# หรือใช้ script Python ถ้า data ไม่มาก (< 10k rows):
python3 scripts/migrate_sqlite_to_postgres.py
```

> สำหรับ NamoNexus ซึ่งเป็น LAN Demo → Production ครั้งแรก
> มักไม่มี production data ใน SQLite ที่ต้อง migrate
> สามารถเริ่มจาก `alembic upgrade head` บน PostgreSQL ที่ว่างเปล่าได้เลย

---

## Quick Reference

```bash
# Local dev (SQLite) — ไม่ต้องทำอะไรเพิ่ม
# app.py ยังคง call Base.metadata.create_all() สำหรับ SQLite path

# Production (PostgreSQL) — ใช้ alembic เท่านั้น
alembic upgrade head
```
