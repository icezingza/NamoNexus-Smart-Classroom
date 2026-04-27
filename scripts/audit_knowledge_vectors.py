#!/usr/bin/env python3
"""
Namo Core - Knowledge Vector Quality Audit Script
ใช้สำหรับตรวจสอบจำนวนและความสะอาดของข้อมูลพระไตรปิฎกก่อนนำไปใช้งานจริง (Production)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_METADATA_PATHS = [
    PROJECT_ROOT / "knowledge" / "tripitaka_main" / "tripitaka_metadata.json",
    PROJECT_ROOT / "knowledge" / "tripitaka" / "tripitaka_metadata.json",
    PROJECT_ROOT
    / "backend"
    / "namo_core"
    / "data"
    / "knowledge"
    / "tripitaka"
    / "tripitaka_metadata.json",
]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "reports"
HTML_PATTERN = re.compile(r"<[^>]+>")
SEPARATOR_LINE_PATTERN = re.compile(r"^[_\-=.\s]{4,}$")
BRACKET_REFERENCE_PATTERN = re.compile(r"^\[[^\]]+\]$")
NUMBERED_ITEM_PATTERN = re.compile(r"^(?:แผน|ข้อ|บทที่|หมวด|ตอนที่|[0-9๐-๙]+[.)])")
CHUNK_INDEX_PATTERN = re.compile(r"_c(\d+)$")
PAGE_LABEL_PATTERN = re.compile(r"^(?:หน้า|เล่ม(?:ที่)?|ภาค(?:ที่)?|ตอนที่)\s*[0-9๐-๙]+")

DEPENDENT_START_CHARS = set("ะัาำิีึืฺุู็่้๊๋์ํ๎ๆ")
DEPENDENT_END_CHARS = set("ัิีึืฺุู็่้๊๋์ํ๎")
CLEAN_ENDINGS = (".", "!", "?", "ฯ", "ฯลฯ", "]", "”", '"', "'")
FOOTER_KEYWORDS = (
    "[email protected]",
    "กรุณาแจ้งได้ที่",
    "ดาวน์โหลดโปรแกรมพระไตรปิฎก",
    "ดาวน์โหลดพระไตรปิฎกภาษาไทยฉบับมหาจุฬาฯ",
)
STRUCTURE_KEYWORDS = (
    "สิกขาบท",
    "วรรค",
    "กัณฑ์",
    "สูตร",
    "นิทาน",
    "คาถา",
    "ภาณวาร",
    "หมวด",
    "บรรพ",
    "ปริเฉท",
    "พระไตรปิฎก",
    "นักธรรม",
)
SUMMARY_KEYWORDS = ("สรุป", "สังเขป", "ใจความ", "โดยย่อ", "โดยสรุป")


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit knowledge vector metadata and short chunk quality."
    )
    parser.add_argument("--metadata-path", type=Path, help="Path to metadata JSON file.")
    parser.add_argument(
        "--short-threshold",
        type=int,
        default=50,
        help="Maximum character length considered a short chunk.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for CSV/JSON reports.",
    )
    parser.add_argument(
        "--export-short-chunks",
        action="store_true",
        help="Export short chunk audit records to CSV and JSON.",
    )
    parser.add_argument(
        "--semantic-short-audit",
        action="store_true",
        help="Show semantic categories and frequent short-chunk pattern families.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of samples to print per semantic category.",
    )
    return parser.parse_args()


def resolve_metadata_path(explicit_path: Path | None) -> Path:
    if explicit_path:
        return explicit_path
    for candidate in CANDIDATE_METADATA_PATHS:
        if candidate.exists():
            return candidate
    return CANDIDATE_METADATA_PATHS[0]


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def extract_chunk_index(chunk_id: str) -> int | None:
    match = CHUNK_INDEX_PATTERN.search(chunk_id)
    if not match:
        return None
    return int(match.group(1))


def looks_like_verse_or_formula(text: str) -> bool:
    tokens = text.split()
    if len(tokens) < 4:
        return False
    if any(mark in text for mark in (".", "!", "?", "จบ")):
        return False
    short_token_count = sum(1 for token in tokens if len(token) <= 8)
    return short_token_count >= len(tokens) - 1


def detect_pattern_family(text: str, raw_text: str, chunk_id: str) -> str:
    if any(keyword in text for keyword in FOOTER_KEYWORDS):
        return "footer_contact"
    if SEPARATOR_LINE_PATTERN.fullmatch(text):
        return "separator_line"
    if BRACKET_REFERENCE_PATTERN.fullmatch(text):
        return "bracket_reference"
    if any(keyword in text for keyword in SUMMARY_KEYWORDS):
        return "summary_note"
    if PAGE_LABEL_PATTERN.match(text):
        return "page_or_volume_label"
    if NUMBERED_ITEM_PATTERN.match(text):
        return "numbered_list_or_plan"
    if any(keyword in text for keyword in STRUCTURE_KEYWORDS):
        return "section_heading"
    if "จบ." in text or text.endswith("ฯ"):
        return "section_closure"
    if looks_like_verse_or_formula(text):
        return "verse_or_formula_line"

    first_char = text[0]
    last_char = text[-1]
    starts_badly = unicodedata.category(first_char).startswith("M") or first_char in DEPENDENT_START_CHARS
    ends_badly = unicodedata.category(last_char).startswith("M") or last_char in DEPENDENT_END_CHARS

    if starts_badly:
        return "leading_fragment"
    if ends_badly:
        return "trailing_fragment"
    if not text.endswith(CLEAN_ENDINGS) and (extract_chunk_index(chunk_id) or 0) > 0:
        return "trailing_fragment"
    return "other"


def detect_flags(text: str, raw_text: str, chunk_id: str) -> list[str]:
    flags: list[str] = []
    first_char = text[0]
    last_char = text[-1]

    if any(keyword in text for keyword in FOOTER_KEYWORDS):
        flags.append("contains_footer_contact")
    if SEPARATOR_LINE_PATTERN.fullmatch(text):
        flags.append("separator_only")
    if BRACKET_REFERENCE_PATTERN.fullmatch(text):
        flags.append("bracket_reference")
    if any(keyword in text for keyword in SUMMARY_KEYWORDS):
        flags.append("contains_summary_keyword")
    if PAGE_LABEL_PATTERN.match(text):
        flags.append("contains_page_or_volume_label")
    if NUMBERED_ITEM_PATTERN.match(text):
        flags.append("looks_numbered_item")
    if any(keyword in text for keyword in STRUCTURE_KEYWORDS):
        flags.append("contains_structure_keyword")
    if looks_like_verse_or_formula(text):
        flags.append("looks_like_verse_or_formula")
    if "\n" in raw_text:
        flags.append("contains_newline")
    if unicodedata.category(first_char).startswith("M") or first_char in DEPENDENT_START_CHARS:
        flags.append("starts_with_dependent_mark")
    if unicodedata.category(last_char).startswith("M") or last_char in DEPENDENT_END_CHARS:
        flags.append("ends_with_dependent_mark")
    if not text.endswith(CLEAN_ENDINGS):
        flags.append("no_clean_sentence_end")

    chunk_index = extract_chunk_index(chunk_id)
    if chunk_index is not None and chunk_index > 0:
        flags.append("chunk_index_gt_zero")
    return flags


def semantic_category_from_pattern(pattern_family: str, text: str, chunk_id: str) -> str:
    if pattern_family in {"footer_contact", "separator_line"}:
        return "artifact_noise"
    if pattern_family in {
        "bracket_reference",
        "summary_note",
        "page_or_volume_label",
        "numbered_list_or_plan",
        "section_heading",
        "section_closure",
        "verse_or_formula_line",
    }:
        return "meaningful_structural"
    if pattern_family in {"leading_fragment", "trailing_fragment"}:
        return "suspected_fragment"
    if text.endswith(CLEAN_ENDINGS) or (extract_chunk_index(chunk_id) == 0):
        return "meaningful_content"
    return "suspected_fragment"


def classify_short_chunk(item: dict, short_threshold: int) -> dict | None:
    raw_text = item.get("text", "")
    if not raw_text.strip():
        return None

    text = normalize_text(raw_text)
    raw_length = len(raw_text)
    if raw_length >= short_threshold:
        return None

    chunk_id = item.get("chunk_id", "")
    pattern_family = detect_pattern_family(text, raw_text, chunk_id)
    flags = detect_flags(text, raw_text, chunk_id)
    semantic_category = semantic_category_from_pattern(pattern_family, text, chunk_id)

    return {
        "chunk_id": chunk_id,
        "title": item.get("title", ""),
        "source_url": item.get("source_url", ""),
        "length": raw_length,
        "normalized_length": len(text),
        "text": text,
        "semantic_category": semantic_category,
        "pattern_family": pattern_family,
        "flags": flags,
        "flags_text": "|".join(flags),
    }


def bucket_short_length(length: int) -> str:
    if length < 10:
        return "01-09"
    if length < 20:
        return "10-19"
    if length < 30:
        return "20-29"
    if length < 40:
        return "30-39"
    return "40-49"


def build_short_chunk_records(metadata: list[dict], short_threshold: int) -> list[dict]:
    records: list[dict] = []
    for item in metadata:
        record = classify_short_chunk(item, short_threshold)
        if record:
            records.append(record)
    return records


def collect_samples(records: list[dict], key: str, sample_size: int) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        group_name = record[key]
        if len(grouped[group_name]) < sample_size:
            grouped[group_name].append(record)
    return grouped


def write_short_chunk_reports(
    records: list[dict],
    summary: dict,
    output_dir: Path,
    source_label: str,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{source_label}_short_chunks.csv"
    json_path = output_dir / f"{source_label}_short_chunks.json"
    summary_path = output_dir / f"{source_label}_audit_summary.json"

    fieldnames = [
        "chunk_id",
        "title",
        "source_url",
        "length",
        "normalized_length",
        "semantic_category",
        "pattern_family",
        "flags_text",
        "text",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record[field] for field in fieldnames})

    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(records, json_file, ensure_ascii=False, indent=2)

    with open(summary_path, "w", encoding="utf-8") as summary_file:
        json.dump(summary, summary_file, ensure_ascii=False, indent=2)

    return csv_path, json_path, summary_path


def run_audit(args: argparse.Namespace) -> int:
    metadata_path = resolve_metadata_path(args.metadata_path)

    print("==================================================")
    print("  NamoNexus Knowledge Base - Data Quality Audit")
    print("==================================================")

    if not metadata_path.exists():
        print(f"[❌] ไม่พบไฟล์ Metadata ที่: {metadata_path}")
        print("     กรุณาตรวจสอบว่ารันสคริปต์ master_ingestion.py เสร็จสมบูรณ์แล้วหรือไม่")
        return 1

    print(f"[*] กำลังโหลดข้อมูลจาก: {metadata_path}")
    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)

    total_chunks = len(metadata)
    empty_chunks = 0
    html_leak_chunks = 0
    total_chars = 0

    for item in metadata:
        text = item.get("text", "")
        total_chars += len(text)
        if not text.strip():
            empty_chunks += 1
        if HTML_PATTERN.search(text):
            html_leak_chunks += 1

    short_records = build_short_chunk_records(metadata, args.short_threshold)
    avg_chars = total_chars / total_chunks if total_chunks > 0 else 0
    short_chunks = len(short_records)

    semantic_counts = Counter(record["semantic_category"] for record in short_records)
    pattern_counts = Counter(record["pattern_family"] for record in short_records)
    flag_counts = Counter(flag for record in short_records for flag in record["flags"])
    length_buckets = Counter(bucket_short_length(record["length"]) for record in short_records)

    print("\n📊 ────────── รายงานผลการตรวจสอบ ────────── 📊")
    print(f"  จำนวน Vector (Chunks) ทั้งหมด : {total_chunks:,} รายการ")
    print(f"  ความยาวเฉลี่ยต่อ Chunk        : {avg_chars:,.2f} ตัวอักษร")
    print("  ----------------------------------------")
    print(f"  🚨 ข้อมูลที่เป็นค่าว่าง (Empty) : {empty_chunks:,} รายการ")
    print(f"  ⚠️ ข้อมูลที่สั้นเกินไป (<{args.short_threshold} ตัว) : {short_chunks:,} รายการ")
    print(f"  🐛 ข้อมูลที่มี HTML หลุดรอดมา  : {html_leak_chunks:,} รายการ")
    print("==================================================")
    if empty_chunks == 0 and html_leak_chunks == 0:
        print("✅ ข้อมูลมีความสะอาดสูงมาก พร้อมใช้งานใน Production!")

    samples_by_semantic = collect_samples(short_records, "semantic_category", args.sample_size)
    samples_by_pattern = collect_samples(short_records, "pattern_family", args.sample_size)

    if args.semantic_short_audit:
        print("\n🧠 ───── Semantic Audit ของ Short Chunks ─────")
        for category, count in semantic_counts.most_common():
            print(f"  - {category:20s} : {count:,}")

        print("\n🧩 หมวดหมู่ย่อยที่พบบ่อย (Pattern Families)")
        for family, count in pattern_counts.most_common(10):
            print(f"  - {family:20s} : {count:,}")

        print("\n📏 การกระจายตามช่วงความยาว")
        for bucket, count in sorted(length_buckets.items()):
            print(f"  - {bucket} ตัวอักษร : {count:,}")

        print("\n🏷️ สัญญาณที่พบซ้ำบ่อย")
        for flag, count in flag_counts.most_common(10):
            print(f"  - {flag:26s} : {count:,}")

        print("\n🔍 ตัวอย่างต่อหมวด semantic")
        for category, sample_rows in samples_by_semantic.items():
            print(f"  [{category}]")
            for record in sample_rows:
                print(f"    • {record['chunk_id']} ({record['length']}): {record['text']}")

    summary = {
        "metadata_path": str(metadata_path),
        "total_chunks": total_chunks,
        "average_chars_per_chunk": round(avg_chars, 2),
        "empty_chunks": empty_chunks,
        "short_chunk_threshold": args.short_threshold,
        "short_chunks": short_chunks,
        "html_leak_chunks": html_leak_chunks,
        "semantic_category_counts": dict(semantic_counts),
        "pattern_family_counts": dict(pattern_counts),
        "flag_counts": dict(flag_counts),
        "length_bucket_counts": dict(length_buckets),
        "samples_by_semantic_category": samples_by_semantic,
        "samples_by_pattern_family": samples_by_pattern,
    }

    if args.export_short_chunks:
        source_label = metadata_path.parent.name
        csv_path, json_path, summary_path = write_short_chunk_reports(
            records=short_records,
            summary=summary,
            output_dir=args.output_dir,
            source_label=source_label,
        )
        print("\n💾 บันทึกรายงานแล้ว")
        print(f"  - CSV   : {csv_path}")
        print(f"  - JSON  : {json_path}")
        print(f"  - Summary: {summary_path}")

    return 0


if __name__ == "__main__":
    configure_console()
    raise SystemExit(run_audit(parse_args()))
