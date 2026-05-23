# 5-Tier Memory & RAG

เอกสารนี้รวบรวมโครงสร้างข้อมูลและกระบวนการจัดการความรู้ (Knowledge Management) ของ NRE v6.2.0

## 1. Dual-Source RAG
ระบบสืบค้นหลักทำงานคู่ขนานผ่าน 2 ส่วน:
1. **Tripitaka (Primary):** พระไตรปิฎก 171,357 Vectors (ครอบคลุมเล่ม 1-45 สมบูรณ์ 100%)
2. **Global Library (Secondary):** คลังหนังสือนอกพระไตรปิฎก (23 เล่ม / FAISS indexes)

ระบบจะทำ Pre-warm ทั้งสองแหล่งในขั้นตอน Startup (ใช้ `asyncio.gather`) เพื่อรับประกันให้ First Query ตอบสนองได้เร็วกว่า `< 200ms`

## 2. FAISS Index & Embeddings
- **Model:** `paraphrase-multilingual-MiniLM-L12-v2` (Dimensions: 384)
- **Path:** `knowledge/tripitaka_main/tripitaka_index.faiss`
- **Total Index Size:** ~249 MB
- **Location:** จัดเก็บที่ Google Cloud Storage `gs://namo-classroom-models/tripitaka_main/` และโหลดลงมาในตอน Startup อัตโนมัติด้วย `gcs_assets.py`

## 3. Persistent Layer & Semantic Cache
- **PostgreSQL (Cloud SQL):** เป็นฐานข้อมูลหลักสำหรับการเก็บ Log และ Session (Alembic ทำหน้าทื่ Migrate)
- **Semantic Cache:** อยู่ใน Layer ของหน่วยความจำ (In-Memory LRU 500 entries, 5 นาที TTL) เพื่อลดภาระการค้นหาซ้ำซ้อน หากถามคำถามเดิม (< 2ms)
- **Redis State:** ใช้สำหรับการทำ Pub/Sub เพื่อส่งข้อมูลหาหน้าจอ Display และเชื่อมต่อ API ภายนอก
