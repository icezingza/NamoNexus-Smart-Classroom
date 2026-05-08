import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from namo_core.services.knowledge.knowledge_service import KnowledgeService
from namo_core.services.knowledge.global_library_retriever import get_global_library_retriever

async def test_parallel_search():
    print("--- Testing Parallel Async Search ---")
    ks = KnowledgeService()
    query = "อริยสัจ 4"
    results = await ks.search_async(query, top_k=5)
    print(f"Results for '{query}': {len(results)} items found.")
    for r in results[:3]:
        print(f" - [{r.get('source')}] {r.get('title')} (score: {r.get('score'):.4f})")
    assert len(results) > 0, "Should return at least one result"

async def test_skill_sync_logic():
    print("\n--- Testing Skill Sync Logic (Ingestion) ---")
    retriever = get_global_library_retriever()
    initial_book_count = len(retriever.books)
    
    # Mock document ingestion
    description = "Test Skill"
    file_contents = [b"Dhamma is the truth of nature. Peace comes from within."]
    file_names = ["test_dhamma.txt"]
    
    all_chunks = []
    for content, name in zip(file_contents, file_names):
        text = content.decode('utf-8')
        all_chunks.append({
            "text": text,
            "title": name,
            "source": "skill_sync_test",
            "description": description
        })
    
    texts = [c["text"] for c in all_chunks]
    vecs = retriever.model.encode(texts, normalize_embeddings=True).astype("float32")
    retriever.add_document(all_chunks, vecs)
    
    new_book_count = len(retriever.books)
    print(f"Initial books: {initial_book_count}, New books: {new_book_count}")
    assert new_book_count == initial_book_count + 1, "Should have added one more 'book' index"
    
    # Verify search finds the new skill
    results = retriever.search("Dhamma truth nature", top_k=1)
    print(f"Search for 'Dhamma truth nature' in new skill: {results[0].get('title')} (score: {results[0].get('score'):.4f})")
    assert results[0]["source"] == "skill_sync_test"

async def main():
    try:
        # Pre-warm (GlobalLibraryRetriever needs to be initialized)
        get_global_library_retriever()
        
        await test_parallel_search()
        await test_skill_sync_logic()
        print("\n✅ ALL TESTS PASSED: NRE v5.0.0 Sovereign Architecture Verified.")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
