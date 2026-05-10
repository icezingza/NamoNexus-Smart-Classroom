# 📋 PHASE 1: Books 11-22 Acquisition Strategy
**Status**: Ready for Execution  
**Target**: Sutta Pitaka Middle (Books 11-22) — 12,675+ suttas

## Current Corpus Status (2026-05-11)
- Books Present: 1-10, 23-45 (33/45 books)
- Books Missing: 11-22 (12/45 books)
- Total Vectors: 168,861
- Corpus Completeness: **73.3%**

## Books 11-22 Breakdown
- Books 11-14: Digha Nikaya (DN) - 34 suttas → ~5,000 chunks
- Books 15-18: Majjhima Nikaya (MN) - 152 suttas → ~15,000 chunks
- Books 19-21: Samyutta Nikaya (SN) - 2,889 suttas → ~35,000 chunks
- Books 22: Anguttara Nikaya (AN) - 9,596 suttas → ~60,000 chunks

**Post-Integration**: 168,861 + ~115,000 = **283,861 vectors** ✨

## PHASE 1: VERIFICATION OPTIONS

### Option A: SuttaCentral (RECOMMENDED)
✅ Complete Pali texts + English translations
✅ CC BY-NC-ND license (educational use)
✅ Structured JSON API
✅ Fastest integration path

### Option B: Buddhadust (FALLBACK)
✅ Public domain (safest for commercial)
✅ Complete Pali + English
✅ No licensing restrictions
⚠️  HTML scraping required

### Option C: GRETIL (BACKUP)
✅ Raw academic Pali texts
⚠️  XML/SGML parsing required
⚠️  No English translations

## INTEGRATION STEPS (Once Books 11-22 Acquired)

1. Standardize to chunk format (chunk_id, title, text, source_url)
2. Deduplicate with Books 1-10
3. Run batch_vectorizer.py for FAISS indexing
4. Rebuild master index via rebuild_v45_index.py
5. Update metadata (total_vectors → ~283,861, books 1-45)
6. Verify quality (zero empty chunks, <200ms query latency)

## DECISION FOR พี่

Recommended: SuttaCentral (Option A)

Next Steps:
1. Verify SuttaCentral API when internet available
2. Download DN (Books 11-14) as proof-of-concept
3. Standardize & integrate into knowledge/tripitaka_main/
4. Scale to MN, SN, AN (Books 15-22)

นะโมพร้อมเริ่ม Phase 1 Verification ทันที ✅
