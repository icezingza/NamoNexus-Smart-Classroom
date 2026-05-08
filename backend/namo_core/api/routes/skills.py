from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
import asyncio
from typing import List
from namo_core.services.knowledge.global_library_retriever import get_global_library_retriever

router = APIRouter(prefix="/skills", tags=["skills"])

async def process_document(description: str, file_contents: list[bytes], file_names: list[str]):
    import logging
    logger = logging.getLogger(__name__)
    
    retriever = get_global_library_retriever()
    
    all_chunks = []
    # Basic text extraction and chunking
    for content, name in zip(file_contents, file_names):
        text = content.decode('utf-8', errors='ignore')
        words = text.split()
        chunk_size = 150
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            if chunk.strip():
                all_chunks.append({
                    "text": chunk,
                    "title": name,
                    "source": "skill_sync",
                    "description": description
                })
    
    if not all_chunks:
        logger.warning("No readable text found in uploaded skills.")
        return
        
    texts = [c["text"] for c in all_chunks]
    
    def encode_and_add():
        vecs = retriever.model.encode(texts, normalize_embeddings=True).astype("float32")
        retriever.add_document(all_chunks, vecs)
        logger.info(f"Successfully synced {len(all_chunks)} skill chunks to Global Library.")
        
    try:
        await asyncio.to_thread(encode_and_add)
    except Exception as exc:
        logger.error(f"Failed to encode and add skill chunks: {exc}")

@router.post("/sync")
async def sync_skill(
    background_tasks: BackgroundTasks,
    description: str = Form(...),
    files: List[UploadFile] = File(...)
):
    contents = []
    names = []
    for file in files:
        contents.append(await file.read())
        names.append(file.filename)
        
    background_tasks.add_task(process_document, description, contents, names)
    return {"message": "Skill sync started", "files_received": len(files)}