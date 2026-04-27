#!/usr/bin/env python3
"""
Reusable quality filters for Tripitaka ingestion pipelines.

This module turns the short-chunk audit heuristics into executable
Hard/Soft filter decisions that can run before vector embedding.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections import Counter

HTML_PATTERN = re.compile(r"<[^>]+>")
SEPARATOR_LINE_PATTERN = re.compile(r"^[_\-=.\s]{4,}$")
BRACKET_REFERENCE_PATTERN = re.compile(r"^\[[^\]]+\]$")
NUMBERED_ITEM_PATTERN = re.compile(r"^(?:แผน|ข้อ|บทที่|หมวด|ตอนที่|[0-9๐-๙]+[.)])")
CHUNK_INDEX_PATTERN = re.compile(r"_c(\d+)$")
CHUNK_STEM_PATTERN = re.compile(r"_c\d+$")
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
ORPHAN_FOOTER_TAILS = {
    "]",
    "d]",
    "ed]",
    "ted]",
    "cted]",
    "ected]",
    "tected]",
    "rotected]",
    "protected]",
    "il protected]",
}
TEXT_FIELD_CANDIDATES = ("text", "content", "golden_sentence")


def detect_text_field(record: dict) -> str:
    for candidate in TEXT_FIELD_CANDIDATES:
        if candidate in record:
            return candidate
    return "text"


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def extract_chunk_index(chunk_id: str) -> int | None:
    match = CHUNK_INDEX_PATTERN.search(chunk_id or "")
    if not match:
        return None
    return int(match.group(1))


def extract_chunk_stem(chunk_id: str) -> str:
    if not chunk_id:
        return ""
    return CHUNK_STEM_PATTERN.sub("", chunk_id)


def looks_like_verse_or_formula(text: str) -> bool:
    tokens = text.split()
    if len(tokens) < 4:
        return False
    if any(mark in text for mark in (".", "!", "?", "จบ")):
        return False
    short_token_count = sum(1 for token in tokens if len(token) <= 8)
    return short_token_count >= len(tokens) - 1


def looks_like_orphan_footer_fragment(text: str) -> bool:
    lowered = text.strip().lower()
    if lowered in ORPHAN_FOOTER_TAILS:
        return True
    return bool(re.search(r"(?:protected|rotected|otected|tected|ected|cted|ted)\]$", lowered))


def detect_pattern_family(text: str, raw_text: str, chunk_id: str) -> str:
    chunk_index = extract_chunk_index(chunk_id)

    if any(keyword in text for keyword in FOOTER_KEYWORDS) or looks_like_orphan_footer_fragment(text):
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
    if chunk_index is not None and chunk_index > 0 and not text.endswith(CLEAN_ENDINGS):
        return "trailing_fragment"
    return "other"


def detect_flags(text: str, raw_text: str, chunk_id: str) -> list[str]:
    flags: list[str] = []
    first_char = text[0]
    last_char = text[-1]
    chunk_index = extract_chunk_index(chunk_id)

    if any(keyword in text for keyword in FOOTER_KEYWORDS):
        flags.append("contains_footer_contact")
    if looks_like_orphan_footer_fragment(text):
        flags.append("contains_orphan_footer_tail")
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
    if chunk_index is not None and chunk_index > 0:
        flags.append("chunk_index_gt_zero")

    return flags


def semantic_category_from_pattern(pattern_family: str, text: str, chunk_id: str) -> str:
    chunk_index = extract_chunk_index(chunk_id)
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
    if text.endswith(CLEAN_ENDINGS) or chunk_index in {None, 0}:
        return "meaningful_content"
    return "suspected_fragment"


def inspect_record_quality(
    record: dict,
    *,
    text_field: str | None = None,
    short_threshold: int = 50,
) -> dict:
    resolved_text_field = text_field or detect_text_field(record)
    raw_text = record.get(resolved_text_field, "") or ""
    normalized_text = normalize_text(raw_text)
    chunk_id = record.get("chunk_id", "")

    report = {
        "text_field": resolved_text_field,
        "raw_text": raw_text,
        "normalized_text": normalized_text,
        "raw_length": len(raw_text),
        "normalized_length": len(normalized_text),
        "semantic_category": "long_or_unclassified",
        "pattern_family": "none",
        "flags": [],
        "hard_reason": None,
        "recommended_action": "keep",
    }

    if not raw_text.strip():
        report["semantic_category"] = "empty"
        report["pattern_family"] = "empty"
        report["hard_reason"] = "empty_text"
        report["recommended_action"] = "drop"
        return report

    if HTML_PATTERN.search(raw_text):
        report["semantic_category"] = "html_noise"
        report["pattern_family"] = "html_leak"
        report["hard_reason"] = "html_leak"
        report["recommended_action"] = "drop"
        return report

    if len(raw_text) >= short_threshold:
        return report

    report["pattern_family"] = detect_pattern_family(normalized_text, raw_text, chunk_id)
    report["semantic_category"] = semantic_category_from_pattern(
        report["pattern_family"],
        normalized_text,
        chunk_id,
    )
    report["flags"] = detect_flags(normalized_text, raw_text, chunk_id)

    if report["semantic_category"] == "artifact_noise":
        report["hard_reason"] = report["pattern_family"]
        report["recommended_action"] = "drop"
    elif report["semantic_category"] == "suspected_fragment":
        report["recommended_action"] = "merge_prev"
    elif report["semantic_category"] == "meaningful_structural":
        report["recommended_action"] = "keep_low_priority"

    return report


def can_merge_with_previous(previous: dict | None, current: dict, *, text_field: str) -> bool:
    if previous is None:
        return False

    previous_chunk = previous.get("chunk_id", "")
    current_chunk = current.get("chunk_id", "")
    if previous_chunk and current_chunk:
        if extract_chunk_stem(previous_chunk) == extract_chunk_stem(current_chunk):
            return True

    previous_title = previous.get("title", "")
    current_title = current.get("title", "")
    previous_url = previous.get("source_url", "")
    current_url = current.get("source_url", "")

    if previous_title and current_title and previous_title == current_title:
        if previous_url and current_url:
            return previous_url == current_url
        return True

    return False


def merge_texts(previous_text: str, current_text: str, *, pattern_family: str) -> str:
    left = previous_text.rstrip()
    right = current_text.lstrip()

    if not left:
        return right
    if not right:
        return left

    if pattern_family == "leading_fragment":
        joiner = ""
    elif right[:1] in ".,;:!?)]ฯ":
        joiner = ""
    elif left.endswith(("\n", " ")):
        joiner = ""
    else:
        joiner = " "

    return f"{left}{joiner}{right}"


def format_quality_stats(stats: dict) -> list[str]:
    lines = [
        "Quality filter summary:",
        f"  Input records           : {stats['input_records']:,}",
        f"  Output records          : {stats['output_records']:,}",
        f"  Hard-dropped records    : {stats['hard_dropped_records']:,}",
        f"  Soft-merged fragments   : {stats['soft_merged_records']:,}",
        f"  Kept unmerged fragments : {stats['soft_kept_fragments']:,}",
    ]

    if stats["hard_drop_reasons"]:
        lines.append("  Hard drop reasons:")
        for reason, count in stats["hard_drop_reasons"].most_common():
            lines.append(f"    - {reason}: {count:,}")

    if stats["soft_merge_pattern_families"]:
        lines.append("  Soft merge pattern families:")
        for family, count in stats["soft_merge_pattern_families"].most_common():
            lines.append(f"    - {family}: {count:,}")

    return lines


def apply_quality_filters(
    records: list[dict],
    *,
    text_field: str | None = None,
    short_threshold: int = 50,
    merge_fragments: bool = True,
) -> tuple[list[dict], dict]:
    filtered_records: list[dict] = []
    stats = {
        "input_records": len(records),
        "output_records": 0,
        "hard_dropped_records": 0,
        "soft_merged_records": 0,
        "soft_kept_fragments": 0,
        "hard_drop_reasons": Counter(),
        "soft_merge_pattern_families": Counter(),
        "semantic_categories": Counter(),
        "pattern_families": Counter(),
    }

    for record in records:
        resolved_text_field = text_field or detect_text_field(record)
        quality = inspect_record_quality(
            record,
            text_field=resolved_text_field,
            short_threshold=short_threshold,
        )

        stats["semantic_categories"][quality["semantic_category"]] += 1
        stats["pattern_families"][quality["pattern_family"]] += 1

        if quality["recommended_action"] == "drop":
            stats["hard_dropped_records"] += 1
            stats["hard_drop_reasons"][quality["hard_reason"] or "unknown"] += 1
            continue

        cloned = copy.deepcopy(record)

        if (
            quality["recommended_action"] == "merge_prev"
            and merge_fragments
            and can_merge_with_previous(
                filtered_records[-1] if filtered_records else None,
                cloned,
                text_field=resolved_text_field,
            )
        ):
            previous = filtered_records[-1]
            previous_text = previous.get(resolved_text_field, "") or ""
            current_text = cloned.get(resolved_text_field, "") or ""
            previous[resolved_text_field] = merge_texts(
                previous_text,
                current_text,
                pattern_family=quality["pattern_family"],
            )
            stats["soft_merged_records"] += 1
            stats["soft_merge_pattern_families"][quality["pattern_family"]] += 1
            continue

        if quality["recommended_action"] == "merge_prev":
            stats["soft_kept_fragments"] += 1

        filtered_records.append(cloned)

    stats["output_records"] = len(filtered_records)
    return filtered_records, stats
