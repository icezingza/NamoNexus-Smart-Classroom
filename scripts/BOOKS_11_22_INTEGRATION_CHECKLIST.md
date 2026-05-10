
# Books 11-22 Integration Checklist (When Real Data Available)

## PHASE 2: ACQUISITION ✓ (Scripts ready)
- [ ] Run: python scripts/fetch_books_11_22_suttacentral.py
- [ ] Output: knowledge/tripitaka_main/books_11_22_raw/{DN,MN,SN,AN}_raw.json
- [ ] Verify: ~12,671 suttas downloaded

## PHASE 3: STANDARDIZATION & VECTORIZATION
- [ ] Run: python scripts/standardize_books_11_22.py
  - Input: books_11_22_raw/*.json
  - Output: chunks/chunk_books_11_22.json (~115,000 chunks)
- [ ] Run: python backend/namo_core/scripts/batch_vectorizer.py \
    --input knowledge/tripitaka_main/chunks/chunk_books_11_22.json \
    --output knowledge/tripitaka_main/batch_indexes/books_11_22.index
- [ ] Verify FAISS index created (~600 MB)

## PHASE 4: MASTER INDEX REBUILD
- [ ] Run: cd knowledge/tripitaka_main && python rebuild_v45_index.py
- [ ] Verify: tripitaka_v45.index rebuilt (with all 37 book indexes)
- [ ] Update: tripitaka_metadata.json (total_vectors → 283,861)

## VERIFICATION
- [ ] Run: python scripts/verify_books_11_22_integration.py
- [ ] Check: Total vectors increased to ~283,861
- [ ] Check: Books 1-45 all present
- [ ] Test: Query latency < 200ms (post-warm)

## DEPLOYMENT
- [ ] Update: CLAUDE.md with new corpus statistics
- [ ] Commit: git add knowledge/ scripts/ CLAUDE.md
- [ ] Commit: git commit -m "Feat(P23): Complete Books 11-22 integration"
- [ ] Push: git push origin main
