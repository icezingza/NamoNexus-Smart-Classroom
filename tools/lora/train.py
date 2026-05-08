"""
train.py — Namo-LoRA QLoRA Fine-tuning Script

Uses HuggingFace PEFT + TRL SFTTrainer + BitsAndBytes 4-bit quantization.
Designed to run on a single GPU (Lenovo workstation RTX 3060/4060+).

VRAM estimates (batch=2, grad_accum=8, seq=2048):
  8B  model @ 4-bit: ~8–10 GB VRAM   ← fits RTX 3060 12GB
  7B  model @ 4-bit: ~7–9  GB VRAM

Run:
  # Step 1: prepare dataset (one-time)
  python tools/lora/prepare_data.py

  # Step 2: train
  python tools/lora/train.py

  # Step 3: evaluate
  python tools/lora/evaluate.py

  # Step 4: merge & export
  python tools/lora/export_model.py
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Guard: check required packages before heavy imports
# ---------------------------------------------------------------------------
_REQUIRED = ["transformers", "peft", "trl", "bitsandbytes", "datasets", "accelerate"]
_missing = [p for p in _REQUIRED if __import__("importlib").util.find_spec(p) is None]
if _missing:
    logger.error("Missing packages: %s", _missing)
    logger.error("Install with: pip install -r tools/lora/requirements.txt")
    sys.exit(1)

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

from config import LoRAConfig  # noqa: E402 (run from tools/lora/)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _check_dataset(cfg: LoRAConfig) -> None:
    """Abort early if training data is missing."""
    train_path = Path(cfg.dataset_path)
    if not train_path.exists():
        logger.error("Training data not found: %s", train_path)
        logger.error("Run: python tools/lora/prepare_data.py")
        sys.exit(1)
    line_count = sum(1 for _ in train_path.open(encoding="utf-8"))
    if line_count < 10:
        logger.warning("Training set is very small (%d examples). Consider adding more data.", line_count)
    logger.info("Training examples: %d", line_count)


def _load_model_and_tokenizer(cfg: LoRAConfig):
    """Load quantized base model + tokenizer."""
    hf_token = os.environ.get(cfg.hf_token_env)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=cfg.load_in_4bit,
        bnb_4bit_quant_type=cfg.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=getattr(torch, cfg.bnb_4bit_compute_dtype),
        bnb_4bit_use_double_quant=cfg.bnb_4bit_use_double_quant,
    )

    logger.info("Loading base model: %s", cfg.base_model)
    model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        token=hf_token,
    )
    model.config.use_cache = False       # required for gradient checkpointing
    model.config.pretraining_tp = 1

    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        cfg.base_model,
        trust_remote_code=True,
        token=hf_token,
    )
    # LLaMA / Typhoon models often have no pad token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    tokenizer.padding_side = "right"  # avoid warning with fp16

    return model, tokenizer


def _apply_lora(model, cfg: LoRAConfig):
    """Prepare model for kbit training and inject LoRA adapters."""
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=cfg.gradient_checkpointing,
    )
    lora_config = LoraConfig(
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        lora_dropout=cfg.lora_dropout,
        target_modules=cfg.target_modules,
        bias=cfg.bias,
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


def _load_datasets(cfg: LoRAConfig):
    """Load train + validation JSONL datasets."""
    data_files: dict[str, str] = {"train": cfg.dataset_path}
    if Path(cfg.val_dataset_path).exists():
        data_files["validation"] = cfg.val_dataset_path

    dataset = load_dataset("json", data_files=data_files)
    logger.info("Dataset loaded: %s", dataset)
    return dataset


def train(cfg: LoRAConfig | None = None) -> None:
    """Main training entry point."""
    if cfg is None:
        cfg = LoRAConfig()

    logger.info("=== Namo-LoRA Training Start ===")
    logger.info("Base model : %s", cfg.base_model)
    logger.info("Output dir : %s", cfg.output_dir)
    logger.info("Epochs     : %d", cfg.num_train_epochs)
    logger.info("LoRA rank  : %d", cfg.lora_r)

    _check_dataset(cfg)

    model, tokenizer = _load_model_and_tokenizer(cfg)
    model = _apply_lora(model, cfg)
    dataset = _load_datasets(cfg)

    training_args = TrainingArguments(
        output_dir=cfg.output_dir,
        num_train_epochs=cfg.num_train_epochs,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        per_device_eval_batch_size=cfg.per_device_eval_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        gradient_checkpointing=cfg.gradient_checkpointing,
        learning_rate=cfg.learning_rate,
        weight_decay=cfg.weight_decay,
        optim=cfg.optim,
        lr_scheduler_type=cfg.lr_scheduler_type,
        warmup_ratio=cfg.warmup_ratio,
        max_grad_norm=cfg.max_grad_norm,
        logging_steps=cfg.logging_steps,
        save_steps=cfg.save_steps,
        eval_steps=cfg.eval_steps if "validation" in dataset else None,
        evaluation_strategy="steps" if "validation" in dataset else "no",
        save_total_limit=cfg.save_total_limit,
        load_best_model_at_end=("validation" in dataset),
        report_to=cfg.report_to,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        # Required for gradient checkpointing + PEFT
        ddp_find_unused_parameters=False,
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        tokenizer=tokenizer,
        args=training_args,
        dataset_text_field=cfg.text_column,
        max_seq_length=cfg.max_seq_length,
        packing=cfg.packing,
    )

    # Resume from checkpoint if available
    checkpoint_path = Path(cfg.output_dir)
    checkpoints = sorted(checkpoint_path.glob("checkpoint-*"))
    resume_from = str(checkpoints[-1]) if checkpoints else None
    if resume_from:
        logger.info("Resuming from checkpoint: %s", resume_from)

    logger.info("Training...")
    trainer.train(resume_from_checkpoint=resume_from)

    logger.info("Saving final adapter...")
    adapter_path = Path(cfg.output_dir) / "final_adapter"
    trainer.model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))
    logger.info("Adapter saved → %s", adapter_path)
    logger.info("=== Training Complete ===")


if __name__ == "__main__":
    # Allow quick override: python train.py --epochs 1 --batch 1
    import argparse
    parser = argparse.ArgumentParser(description="Namo-LoRA fine-tuning")
    parser.add_argument("--model", type=str, help="HuggingFace model ID")
    parser.add_argument("--epochs", type=int, help="Number of training epochs")
    parser.add_argument("--batch", type=int, help="Per-device batch size")
    parser.add_argument("--rank", type=int, help="LoRA rank")
    parser.add_argument("--output", type=str, help="Output directory")
    args = parser.parse_args()

    cfg = LoRAConfig()
    if args.model:
        cfg.base_model = args.model
    if args.epochs:
        cfg.num_train_epochs = args.epochs
    if args.batch:
        cfg.per_device_train_batch_size = args.batch
    if args.rank:
        cfg.lora_r = args.rank
    if args.output:
        cfg.output_dir = args.output

    train(cfg)
