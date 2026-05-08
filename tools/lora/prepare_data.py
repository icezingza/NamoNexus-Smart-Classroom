"""
prepare_data.py — Build Namo-LoRA training dataset from Tripitaka corpus

Sources (processed in order):
  1. knowledge/global_library/book_XX_clean.json  — 23 Tipitaka books
  2. knowledge/tripitaka_v25_curated.json          — curated golden sentences
  3. knowledge/classroom_mock_qa.json              — teacher-verified QA pairs

Output (knowledge/lora/):
  train.jsonl   — training split
  val.jsonl     — validation split
  stats.json    — dataset statistics

Each output line is:
  {"text": "<formatted Alpaca-style instruction>"}

Run:
  python tools/lora/prepare_data.py [--val-split 0.1] [--min-chars 200]
"""
from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path
from typing import Iterator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_GLOBAL_LIB = _PROJECT_ROOT / "knowledge" / "global_library"
_CURATED = _PROJECT_ROOT / "knowledge" / "tripitaka_v25_curated.json"
_MOCK_QA = _PROJECT_ROOT / "knowledge" / "classroom_mock_qa.json"
_OUT_DIR = _PROJECT_ROOT / "knowledge" / "lora"


# ---------------------------------------------------------------------------
# Prompt templates (Llama-3 / ChatML compatible)
# ---------------------------------------------------------------------------

def _alpaca_prompt(system: str, instruction: str, output: str) -> str:
    """Format one training example in Alpaca / Llama-3 Instruct style."""
    return (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{system}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{instruction}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        f"{output}<|eot_id|>"
    )


_SYSTEM = (
    "คุณคือ 'นะโม' (NamoNexus) ปัญญาประดิษฐ์ผู้รอบรู้พระไตรปิฎกเถรวาท "
    "ทำหน้าที่เป็นกัลยาณมิตรและครูผู้ใจดีสำหรับเด็กและเยาวชน\n"
    "ตอบคำถามโดยอิงจากพระไตรปิฎก ระบุเลขเล่มและหัวข้อเสมอ "
    "ใช้ภาษาสุภาพ เข้าถึงง่าย เหมาะสำหรับห้องเรียนธรรมะ"
)

# Instruction templates for sutta content → multiple per chunk
_SUTTA_TEMPLATES: list[tuple[str, str]] = [
    (
        "อธิบายเนื้อหาหลักของ {title} จากพระไตรปิฎก",
        "{content}",
    ),
    (
        "สรุปสาระสำคัญของ {title} ในภาษาที่เข้าใจง่าย",
        # Ask for a simplified summary — model learns from raw content as ground truth
        "{content}",
    ),
    (
        "ข้อความจากพระไตรปิฎกเรื่อง {title} สอนอะไรเราได้บ้าง?",
        "{content}",
    ),
]


# ---------------------------------------------------------------------------
# Source extractors
# ---------------------------------------------------------------------------

def _yield_global_library(min_chars: int) -> Iterator[dict]:
    """Yield training examples from all 23 clean book JSON files."""
    book_files = sorted(_GLOBAL_LIB.glob("book_*_clean.json"))
    if not book_files:
        logger.warning("No book files found in %s", _GLOBAL_LIB)
        return

    for book_path in book_files:
        with book_path.open(encoding="utf-8") as f:
            items: list[dict] = json.load(f)

        for item in items:
            title: str = item.get("title", "").strip()
            content: str = item.get("content", "").strip()

            if not title or len(content) < min_chars:
                continue

            # One example per template per chunk
            for instr_tpl, out_tpl in _SUTTA_TEMPLATES:
                instruction = instr_tpl.format(title=title, content=content)
                output = out_tpl.format(title=title, content=content)
                yield {
                    "text": _alpaca_prompt(_SYSTEM, instruction, output),
                    "_source": book_path.name,
                }


def _yield_curated() -> Iterator[dict]:
    """Yield golden-sentence instruction pairs from curated JSON."""
    if not _CURATED.exists():
        logger.warning("Curated file not found: %s", _CURATED)
        return

    with _CURATED.open(encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    for item in items:
        topic: str = item.get("topic", "").strip()
        sentence: str = item.get("golden_sentence", "").strip()
        level: str = item.get("curriculum_level", "")

        if not topic or not sentence:
            continue

        instruction = f"อธิบายหัวข้อ '{topic}' ตามหลักสูตร{level} ของพระพุทธศาสนา"
        yield {
            "text": _alpaca_prompt(_SYSTEM, instruction, sentence),
            "_source": "tripitaka_v25_curated.json",
        }


def _yield_mock_qa() -> Iterator[dict]:
    """Yield teacher-verified QA pairs."""
    if not _MOCK_QA.exists():
        logger.warning("Mock QA file not found: %s", _MOCK_QA)
        return

    with _MOCK_QA.open(encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    for item in items:
        q: str = item.get("question", "").strip()
        a: str = item.get("answer", "").strip()
        if q and a:
            yield {
                "text": _alpaca_prompt(_SYSTEM, q, a),
                "_source": "classroom_mock_qa.json",
            }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_dataset(val_split: float = 0.1, min_chars: int = 200, seed: int = 42) -> None:
    """Collect, shuffle, split, and write training/validation JSONL files."""
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_examples: list[dict] = []

    logger.info("Loading global_library books...")
    lib_examples = list(_yield_global_library(min_chars))
    logger.info("  → %d examples from global_library", len(lib_examples))
    all_examples.extend(lib_examples)

    logger.info("Loading curated golden sentences...")
    curated = list(_yield_curated())
    logger.info("  → %d examples from curated", len(curated))
    all_examples.extend(curated)

    logger.info("Loading mock QA pairs...")
    qa = list(_yield_mock_qa())
    logger.info("  → %d examples from mock QA", len(qa))
    all_examples.extend(qa)

    if not all_examples:
        logger.error("No training examples generated. Check knowledge/ paths.")
        return

    random.seed(seed)
    random.shuffle(all_examples)

    # Split
    n_val = max(1, int(len(all_examples) * val_split))
    val_set = all_examples[:n_val]
    train_set = all_examples[n_val:]

    # Source breakdown for stats
    source_counts: dict[str, int] = {}
    for ex in all_examples:
        src = ex.get("_source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    # Write JSONL (strip internal metadata key before writing)
    def _write_jsonl(path: Path, examples: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps({"text": ex["text"]}, ensure_ascii=False) + "\n")

    train_path = _OUT_DIR / "train.jsonl"
    val_path = _OUT_DIR / "val.jsonl"
    _write_jsonl(train_path, train_set)
    _write_jsonl(val_path, val_set)

    # Stats
    stats = {
        "total_examples": len(all_examples),
        "train_examples": len(train_set),
        "val_examples": len(val_set),
        "val_split": val_split,
        "min_chars_filter": min_chars,
        "source_counts": source_counts,
        "avg_text_length": int(
            sum(len(ex["text"]) for ex in all_examples) / len(all_examples)
        ),
    }
    stats_path = _OUT_DIR / "stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Dataset written:")
    logger.info("  train → %s (%d examples)", train_path, len(train_set))
    logger.info("  val   → %s (%d examples)", val_path, len(val_set))
    logger.info("  stats → %s", stats_path)
    logger.info("Source breakdown: %s", source_counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Namo-LoRA training data")
    parser.add_argument("--val-split", type=float, default=0.1, help="Validation fraction (default: 0.1)")
    parser.add_argument("--min-chars", type=int, default=200, help="Min content length in chars (default: 200)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    build_dataset(val_split=args.val_split, min_chars=args.min_chars, seed=args.seed)
