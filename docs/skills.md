# Context7 CLI & Skills

คู่มือการใช้เครื่องมือต่างๆ (Skills) ประจำตัว AI Agent เพื่อพัฒนาระบบ NamoNexus

## 1. The Context7 Lookup Workflow
เพื่อป้องกันปัญหาเดาข้อมูล (AI Hallucination) หรือใช้ Library ผิดเวอร์ชัน AI จะต้องใช้ Context7 (npx ctx7) ดึงข้อมูลอัปเดตล่าสุดก่อนเขียนโค้ดเสมอ:
```bash
# 1. ค้นหา Library
npx ctx7@latest library [library-name] "[user-question]"

# 2. ค้นหาเอกสารอัปเดต
npx ctx7@latest docs /[org]/[project] "[full-question-context]"
```

## 2. Pre-Commit Verification Workflow
ก่อนรายงานสถานะสำเร็จ AI จะต้องรัน Linter และ Test เสมอเพื่อยืนยันความพร้อมของโค้ด:
```bash
# ตรวจสอบรูปแบบโค้ด (Python)
ruff check .
ruff format .

# ทดสอบ
python -m pytest tests/
```

## 3. Useful Scripts
ในโฟลเดอร์ `scripts/` มีเครื่องมือที่ใช้งานบ่อยดังนี้:
- **`scripts/health_check.py --full`:** เช็คความพร้อมของระบบ 16/16 ด้าน
- **`scripts/audit_knowledge_vectors.py`:** ตรวจสอบความถูกต้องของ FAISS Index
- **`scripts/verify_cloud_assets.py`:** ตรวจจับและเช็ค GCS Assets ว่าอยู่ครบไหม
- **`scripts/vectorize_books_*.py`:** ชุดสคริปต์สำหรับการ Ingest เนื้อหาพระไตรปิฎก

## 4. Namo-LoRA Tools
เครื่องมือชุดสำหรับการ Train โมเดลส่วนตัว:
- ตำแหน่ง: `tools/lora/`
- รันการเตรียมข้อมูล: `python tools/lora/prepare_data.py`
- เริ่มเทรนโมเดล: `python tools/lora/train.py`
