"""
config.py — Namo-LoRA Training Configuration

All hyperparameters in one place.  Override via CLI args in train.py
or by editing this file.

Recommended base models (Thai-capable):
  scb10x/llama-3-typhoon-v1.5-8b     Thai-optimised, strong instruction following
  openthaigpt/openthaigpt1.5-7b-instruct  Thai-first, lighter
  meta-llama/Llama-3.1-8B-Instruct   Multilingual baseline
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Project root (two levels above this file: tools/lora/ → tools/ → project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class LoRAConfig:
    # ------------------------------------------------------------------ #
    # Model
    # ------------------------------------------------------------------ #
    base_model: str = "scb10x/llama-3-typhoon-v1.5-8b"
    # Set to HF token env var name if the model is gated (e.g. LLaMA-3)
    hf_token_env: str = "HF_TOKEN"

    # ------------------------------------------------------------------ #
    # LoRA adapter
    # ------------------------------------------------------------------ #
    lora_r: int = 8           # Rank — higher = more capacity, more VRAM
    lora_alpha: int = 16      # Scaling: effective_lr = alpha / r
    lora_dropout: float = 0.05
    # Modules to inject LoRA into (LLaMA-3 / Typhoon attention layers)
    target_modules: list[str] = field(
        default_factory=lambda: [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ]
    )
    bias: str = "none"
    task_type: str = "CAUSAL_LM"

    # ------------------------------------------------------------------ #
    # Quantization (QLoRA)
    # ------------------------------------------------------------------ #
    load_in_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"          # nf4 | fp4
    bnb_4bit_compute_dtype: str = "bfloat16"  # bfloat16 | float16
    bnb_4bit_use_double_quant: bool = True     # nested quantization

    # ------------------------------------------------------------------ #
    # Training
    # ------------------------------------------------------------------ #
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 2
    per_device_eval_batch_size: int = 2
    gradient_accumulation_steps: int = 8     # effective batch = 2 × 8 = 16
    gradient_checkpointing: bool = True
    learning_rate: float = 2e-4
    weight_decay: float = 0.001
    optim: str = "paged_adamw_32bit"          # memory-efficient optimiser
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.03
    max_grad_norm: float = 1.0
    max_seq_length: int = 2048
    packing: bool = True                      # TRL SFTTrainer packing for speed

    # ------------------------------------------------------------------ #
    # Dataset
    # ------------------------------------------------------------------ #
    dataset_path: str = str(_PROJECT_ROOT / "knowledge" / "lora" / "train.jsonl")
    val_dataset_path: str = str(_PROJECT_ROOT / "knowledge" / "lora" / "val.jsonl")
    val_split: float = 0.1                    # fraction held out for eval
    # Column in JSONL that holds the pre-formatted training text
    text_column: str = "text"

    # ------------------------------------------------------------------ #
    # Checkpoints & Logging
    # ------------------------------------------------------------------ #
    output_dir: str = str(_PROJECT_ROOT / "tools" / "lora" / "checkpoints")
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100
    save_total_limit: int = 3
    report_to: str = "none"   # "wandb" | "tensorboard" | "none"

    # ------------------------------------------------------------------ #
    # System prompt injected into every training example
    # ------------------------------------------------------------------ #
    system_prompt: str = (
        "คุณคือ 'นะโม' (NamoNexus) ปัญญาประดิษฐ์ผู้รอบรู้พระไตรปิฎกเถรวาท "
        "ทำหน้าที่เป็นกัลยาณมิตรและครูผู้ใจดีสำหรับเด็กและเยาวชน\n"
        "ตอบคำถามโดยอิงจากพระไตรปิฎก ระบุเลขเล่มและหัวข้อเสมอ "
        "ใช้ภาษาสุภาพ เข้าถึงง่าย เหมาะสำหรับห้องเรียนธรรมะ"
    )
