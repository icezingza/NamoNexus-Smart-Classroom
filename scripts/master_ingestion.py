#!/usr/bin/env python3
"""
Namo Core - Knowledge Ingestion Pipeline (FAISS Indexing)

Loads Tripitaka records, applies quality filters, then builds the
FAISS index plus metadata mapping used by the Phase 11 RAG retriever.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tripitaka_quality_filter import (
    apply_quality_filters,
    detect_text_field,
    format_quality_stats,
)


SOURCE_FILE = Path("knowledge/tripitaka_v25_distributed.json")
INDEX_DIR = Path("knowledge/tripitaka")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Tripitaka FAISS index.")
    parser.add_argument("--source-file", type=Path, default=SOURCE_FILE)
    parser.add_argument("--index-dir", type=Path, default=INDEX_DIR)
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--short-threshold", type=int, default=50)
    parser.add_argument(
        "--no-soft-merge",
        action="store_true",
        help="Keep suspected fragments as-is instead of merging into previous chunk.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run quality filtering only and skip embedding/index build.",
    )
    return parser.parse_args()


def load_records(source_file: Path) -> list[dict]:
    with open(source_file, "r", encoding="utf-8") as file:
        return json.load(file)


def select_text_field(records: list[dict]) -> str:
    if not records:
        return "content"
    return detect_text_field(records[0])


def build_embedding_texts(records: list[dict], text_field: str) -> list[str]:
    return [record.get(text_field, "") for record in records if record.get(text_field)]


def print_quality_summary(stats: dict) -> None:
    print("\n🧹 ────────── Quality Filter Report ──────────")
    for line in format_quality_stats(stats):
        print(line)


def run_ingestion(args: argparse.Namespace) -> int:
    print(f"🚀 เริ่มกระบวนการฝังรากฐานความรู้จาก {args.source_file} ...")

    if not args.source_file.exists():
        print(f"❌ ไม่พบไฟล์ข้อมูล: {args.source_file}")
        return 1

    data = load_records(args.source_file)
    if not data:
        print("❌ ไฟล์ข้อมูลว่างเปล่า ไม่สามารถสร้างดัชนีได้")
        return 1

    text_field = select_text_field(data)
    print(f"📥 โหลดข้อมูลสำเร็จ {len(data):,} รายการ")
    print(f"📝 ตรวจพบ text field: '{text_field}'")

    filtered_records, quality_stats = apply_quality_filters(
        data,
        text_field=text_field,
        short_threshold=args.short_threshold,
        merge_fragments=not args.no_soft_merge,
    )
    print_quality_summary(quality_stats)

    if not filtered_records:
        print("❌ ไม่มีข้อมูลเหลือหลังผ่าน quality filter")
        return 1

    texts = build_embedding_texts(filtered_records, text_field)
    metadatas = filtered_records

    if len(texts) != len(metadatas):
        print("❌ จำนวนข้อความกับ metadata ไม่ตรงกันหลังกรองข้อมูล")
        return 1

    print(f"📊 พร้อมสร้าง vector จำนวน {len(texts):,} รายการ")

    if args.dry_run:
        print("🧪 Dry run เสร็จสมบูรณ์ ยังไม่ได้สร้าง embeddings หรือ FAISS index")
        return 0

    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    print(f"🧠 กำลังโหลดสมอง AI: {args.model_name} ...")
    model = SentenceTransformer(args.model_name)

    print("⚡ กำลังคำนวณเวกเตอร์ความหมาย (Embeddings)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")
    faiss.normalize_L2(embeddings)

    print("🏗️ กำลังสร้างดัชนี FAISS...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    args.index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(args.index_dir / "tripitaka_index.faiss"))

    with open(args.index_dir / "tripitaka_metadata.json", "w", encoding="utf-8") as file:
        json.dump(metadatas, file, ensure_ascii=False, indent=2)

    print(f"\n✨ สำเร็จ! สร้างดัชนีความรู้เรียบร้อยที่ {args.index_dir}")
    print(f"📊 สรุป: {index.ntotal:,} เวกเตอร์, มิติ {dimension}")
    return 0


if __name__ == "__main__":
    configure_console()
    raise SystemExit(run_ingestion(parse_args()))
