"""
evaluate.py — Evaluate the Namo-LoRA fine-tuned model

Modes:
  1. Interactive inference  — ask questions and see responses
  2. ROUGE benchmark        — compare against validation JSONL (needs rouge_score)
  3. Reference prompts      — run a fixed set of Dhamma questions

Run:
  python tools/lora/evaluate.py --mode interactive
  python tools/lora/evaluate.py --mode rouge
  python tools/lora/evaluate.py --mode reference
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ADAPTER = str(_PROJECT_ROOT / "tools" / "lora" / "checkpoints" / "final_adapter")

_REFERENCE_PROMPTS: list[dict[str, str]] = [
    {
        "question": "อริยสัจ 4 คืออะไร?",
        "expected_keywords": ["ทุกข์", "สมุทัย", "นิโรธ", "มรรค"],
    },
    {
        "question": "ไตรสรณคมน์หมายถึงอะไร?",
        "expected_keywords": ["พระพุทธ", "พระธรรม", "พระสงฆ์"],
    },
    {
        "question": "อธิบายหลักกรรมตามพระพุทธศาสนา",
        "expected_keywords": ["กรรม", "เจตนา", "ผล"],
    },
    {
        "question": "มงคลสูตรสอนอะไร?",
        "expected_keywords": ["มงคล", "บัณฑิต", "บูชา"],
    },
    {
        "question": "พระนิพพานคืออะไร?",
        "expected_keywords": ["ดับ", "กิเลส", "ทุกข์"],
    },
]


# ---------------------------------------------------------------------------
# Model loader (shared)
# ---------------------------------------------------------------------------

def _load_pipeline(adapter_path: str):
    """Load fine-tuned model as a text-generation pipeline."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        from peft import PeftModel
    except ImportError as e:
        logger.error("Missing package: %s", e)
        logger.error("Install: pip install -r tools/lora/requirements.txt")
        sys.exit(1)

    adapter = Path(adapter_path)
    if not adapter.exists():
        logger.error("Adapter not found: %s", adapter)
        logger.error("Run: python tools/lora/train.py")
        sys.exit(1)

    # Read base model name from adapter_config.json
    adapter_config_path = adapter / "adapter_config.json"
    if not adapter_config_path.exists():
        logger.error("adapter_config.json not found in %s", adapter)
        sys.exit(1)

    with adapter_config_path.open(encoding="utf-8") as f:
        adapter_cfg = json.load(f)
    base_model_name: str = adapter_cfg["base_model_name_or_path"]
    logger.info("Base model: %s", base_model_name)

    tokenizer = AutoTokenizer.from_pretrained(str(adapter), trust_remote_code=True)

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, str(adapter))
    model.eval()

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.1,
        do_sample=True,
        repetition_penalty=1.1,
    )
    return pipe


def _format_prompt(question: str) -> str:
    from config import LoRAConfig
    cfg = LoRAConfig()
    return (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{cfg.system_prompt}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{question}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )


# ---------------------------------------------------------------------------
# Evaluation modes
# ---------------------------------------------------------------------------

def run_interactive(adapter_path: str) -> None:
    """Interactive Q&A with the fine-tuned model."""
    pipe = _load_pipeline(adapter_path)
    print("\n=== Namo-LoRA Interactive Evaluation ===")
    print("พิมพ์ 'quit' เพื่อออก\n")

    while True:
        try:
            question = input("คำถาม: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() == "quit":
            break

        prompt = _format_prompt(question)
        result = pipe(prompt)[0]["generated_text"]
        # Extract only the assistant's response
        marker = "<|start_header_id|>assistant<|end_header_id|>\n\n"
        response = result.split(marker)[-1].strip().split("<|eot_id|>")[0].strip()
        print(f"\nนะโม: {response}\n{'-'*60}\n")


def run_reference(adapter_path: str) -> None:
    """Run fixed reference prompts and check keyword coverage."""
    pipe = _load_pipeline(adapter_path)
    print("\n=== Reference Prompt Evaluation ===\n")

    passed = 0
    for item in _REFERENCE_PROMPTS:
        question: str = item["question"]
        expected: list[str] = item["expected_keywords"]

        prompt = _format_prompt(question)
        result = pipe(prompt)[0]["generated_text"]
        marker = "<|start_header_id|>assistant<|end_header_id|>\n\n"
        response = result.split(marker)[-1].strip().split("<|eot_id|>")[0].strip()

        matched = [kw for kw in expected if kw in response]
        score = len(matched) / len(expected)
        status = "PASS" if score >= 0.5 else "FAIL"
        if score >= 0.5:
            passed += 1

        print(f"[{status}] Q: {question}")
        print(f"       Keywords hit: {matched} ({len(matched)}/{len(expected)})")
        print(f"       A: {response[:200]}...")
        print()

    print(f"Score: {passed}/{len(_REFERENCE_PROMPTS)} ({100*passed//len(_REFERENCE_PROMPTS)}%)")


def run_rouge(adapter_path: str, val_path: str) -> None:
    """Compute ROUGE-L against validation set."""
    try:
        from rouge_score import rouge_scorer as rs
    except ImportError:
        logger.error("rouge_score not installed. Run: pip install rouge-score")
        sys.exit(1)

    val_file = Path(val_path)
    if not val_file.exists():
        logger.error("Val file not found: %s", val_file)
        sys.exit(1)

    pipe = _load_pipeline(adapter_path)
    scorer = rs.RougeScorer(["rougeL"], use_stemmer=False)

    scores: list[float] = []
    with val_file.open(encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]

    # Use first 50 examples for speed
    sample = lines[:50]
    logger.info("Evaluating ROUGE-L on %d examples...", len(sample))

    for item in sample:
        full_text: str = item["text"]
        marker = "<|start_header_id|>assistant<|end_header_id|>\n\n"
        parts = full_text.split(marker)
        if len(parts) < 2:
            continue
        reference = parts[-1].split("<|eot_id|>")[0].strip()

        # Regenerate from everything before the assistant turn
        prompt = marker.join(parts[:-1]) + marker
        result = pipe(prompt)[0]["generated_text"]
        prediction = result.split(marker)[-1].strip().split("<|eot_id|>")[0].strip()

        score = scorer.score(reference, prediction)
        scores.append(score["rougeL"].fmeasure)

    avg = sum(scores) / len(scores) if scores else 0.0
    print(f"\nROUGE-L F1 (n={len(scores)}): {avg:.4f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Namo-LoRA model")
    parser.add_argument(
        "--mode",
        choices=["interactive", "reference", "rouge"],
        default="reference",
        help="Evaluation mode",
    )
    parser.add_argument(
        "--adapter",
        type=str,
        default=_DEFAULT_ADAPTER,
        help="Path to LoRA adapter directory",
    )
    parser.add_argument(
        "--val-file",
        type=str,
        default=str(_PROJECT_ROOT / "knowledge" / "lora" / "val.jsonl"),
        help="Validation JSONL (for --mode rouge)",
    )
    args = parser.parse_args()

    if args.mode == "interactive":
        run_interactive(args.adapter)
    elif args.mode == "reference":
        run_reference(args.adapter)
    elif args.mode == "rouge":
        run_rouge(args.adapter, args.val_file)
