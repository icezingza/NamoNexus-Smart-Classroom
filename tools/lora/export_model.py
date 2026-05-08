"""
export_model.py — Merge LoRA adapter weights into base model and export

Outputs:
  tools/lora/merged/          — HuggingFace merged model (safetensors)
  tools/lora/merged-gguf/     — GGUF for llama.cpp / Ollama (optional)

Run:
  # Merge adapter into base model
  python tools/lora/export_model.py --merge

  # Merge + convert to GGUF (requires llama.cpp installed)
  python tools/lora/export_model.py --merge --gguf --quant q4_k_m
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ADAPTER = _PROJECT_ROOT / "tools" / "lora" / "checkpoints" / "final_adapter"
_MERGED_OUT = _PROJECT_ROOT / "tools" / "lora" / "merged"
_GGUF_OUT = _PROJECT_ROOT / "tools" / "lora" / "merged-gguf"


def merge_adapter(adapter_path: Path, output_path: Path) -> None:
    """Merge LoRA adapter weights into the base model and save."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError as e:
        logger.error("Missing package: %s", e)
        sys.exit(1)

    if not adapter_path.exists():
        logger.error("Adapter not found: %s", adapter_path)
        logger.error("Run: python tools/lora/train.py")
        sys.exit(1)

    # Read base model name
    adapter_config = adapter_path / "adapter_config.json"
    with adapter_config.open(encoding="utf-8") as f:
        cfg = json.load(f)
    base_model_name: str = cfg["base_model_name_or_path"]

    logger.info("Loading base model: %s", base_model_name)
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    logger.info("Loading adapter: %s", adapter_path)
    model = PeftModel.from_pretrained(model, str(adapter_path))

    logger.info("Merging adapter weights into base model (this takes ~1–2 min)...")
    model = model.merge_and_unload()

    output_path.mkdir(parents=True, exist_ok=True)
    logger.info("Saving merged model → %s", output_path)
    model.save_pretrained(str(output_path), safe_serialization=True)

    logger.info("Saving tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(str(adapter_path), trust_remote_code=True)
    tokenizer.save_pretrained(str(output_path))

    logger.info("Merge complete.")


def convert_to_gguf(merged_path: Path, gguf_path: Path, quant: str = "q4_k_m") -> None:
    """Convert merged HF model to GGUF using llama.cpp convert script."""
    # Find llama.cpp convert_hf_to_gguf.py (assumes llama.cpp is installed or cloned)
    convert_candidates = [
        Path("llama.cpp/convert_hf_to_gguf.py"),
        Path.home() / "llama.cpp" / "convert_hf_to_gguf.py",
        Path("/opt/llama.cpp/convert_hf_to_gguf.py"),
    ]
    convert_script = next((p for p in convert_candidates if p.exists()), None)

    if convert_script is None:
        logger.error(
            "llama.cpp convert_hf_to_gguf.py not found. "
            "Clone llama.cpp: git clone https://github.com/ggerganov/llama.cpp"
        )
        sys.exit(1)

    gguf_path.mkdir(parents=True, exist_ok=True)
    gguf_file = gguf_path / f"namo_lora_{quant}.gguf"

    logger.info("Converting to GGUF (quantization: %s)...", quant)
    cmd = [
        sys.executable,
        str(convert_script),
        str(merged_path),
        "--outfile", str(gguf_file),
        "--outtype", quant,
    ]
    logger.info("Command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        logger.error("GGUF conversion failed (exit %d)", result.returncode)
        sys.exit(1)

    logger.info("GGUF saved → %s", gguf_file)
    logger.info("Load in Ollama: ollama create namo-lora -f Modelfile")


def print_modelfile(merged_path: Path, gguf_path: Path, quant: str) -> None:
    """Print a sample Modelfile for Ollama deployment."""
    gguf_file = gguf_path / f"namo_lora_{quant}.gguf"
    from config import LoRAConfig
    cfg = LoRAConfig()

    modelfile = f"""FROM {gguf_file}

SYSTEM "{cfg.system_prompt}"

PARAMETER temperature 0.1
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096
"""
    modelfile_path = gguf_path / "Modelfile"
    modelfile_path.write_text(modelfile, encoding="utf-8")
    print("\n=== Ollama Modelfile ===")
    print(modelfile)
    print(f"Saved → {modelfile_path}")
    print(f"\nDeploy: ollama create namo-lora -f {modelfile_path}")
    print("Run:    ollama run namo-lora")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Namo-LoRA merged model")
    parser.add_argument(
        "--adapter",
        type=str,
        default=str(_DEFAULT_ADAPTER),
        help="Path to LoRA adapter (default: checkpoints/final_adapter)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(_MERGED_OUT),
        help="Output path for merged HF model",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        default=True,
        help="Merge adapter into base model (default: True)",
    )
    parser.add_argument(
        "--gguf",
        action="store_true",
        default=False,
        help="Also convert to GGUF format (requires llama.cpp)",
    )
    parser.add_argument(
        "--quant",
        type=str,
        default="q4_k_m",
        choices=["f16", "q8_0", "q5_k_m", "q4_k_m", "q3_k_m"],
        help="GGUF quantization type (default: q4_k_m)",
    )
    args = parser.parse_args()

    adapter_path = Path(args.adapter)
    output_path = Path(args.output)

    if args.merge:
        merge_adapter(adapter_path, output_path)

    if args.gguf:
        convert_to_gguf(output_path, _GGUF_OUT, args.quant)
        print_modelfile(output_path, _GGUF_OUT, args.quant)
