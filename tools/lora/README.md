# Namo-LoRA — Domain-Adapted Fine-tuning for Tripitaka Corpus

Fine-tunes a Thai-capable base LLM (Typhoon-8B / LLaMA-3) on the NamoNexus
Tripitaka corpus using QLoRA (4-bit quantization + LoRA adapters).

---

## Hardware Requirements

| VRAM   | Usable models        | Batch config |
|--------|----------------------|--------------|
| 8 GB   | 7B @ 4-bit           | batch=1, grad_accum=16 |
| 12 GB  | 8B @ 4-bit ✅ (RTX 3060) | batch=2, grad_accum=8 |
| 16 GB  | 8B @ 4-bit (RTX 4060 Ti) | batch=4, grad_accum=4 |
| 24 GB+ | 13B @ 4-bit          | batch=4, grad_accum=4 |

> ⚠️ bitsandbytes (4-bit quantization) requires Linux + CUDA 11.7+  
> On Windows: use WSL2 with CUDA passthrough

---

## Quick Start

### 1. Install dependencies (WSL2 / Linux with CUDA)
```bash
cd tools/lora
pip install -r requirements.txt
```

### 2. Prepare training data
```bash
python tools/lora/prepare_data.py

# Output:
#   knowledge/lora/train.jsonl  (~300+ examples from 23 books)
#   knowledge/lora/val.jsonl    (10% held out)
#   knowledge/lora/stats.json   (dataset statistics)
```

### 3. Configure (optional)
Edit `tools/lora/config.py` to change:
- `base_model` — swap to a different Thai LLM
- `lora_r` / `lora_alpha` — adjust LoRA capacity
- `num_train_epochs` / `learning_rate` — tune training

### 4. Train
```bash
# From project root:
cd tools/lora && python train.py

# Override from CLI:
python train.py --epochs 1 --batch 1 --rank 16
```

Training ~3 epochs on 300 examples ≈ **15–30 min** on RTX 3060

Checkpoints saved in `tools/lora/checkpoints/`

### 5. Evaluate
```bash
# Fixed reference prompts (no GPU required after export)
python tools/lora/evaluate.py --mode reference

# Interactive chat
python tools/lora/evaluate.py --mode interactive

# ROUGE-L against validation set
python tools/lora/evaluate.py --mode rouge
```

### 6. Export (merge + deploy)
```bash
# Merge adapter into base model → tools/lora/merged/
python tools/lora/export_model.py --merge

# Merge + convert to GGUF (requires llama.cpp)
python tools/lora/export_model.py --merge --gguf --quant q4_k_m

# Deploy with Ollama:
ollama create namo-lora -f tools/lora/merged-gguf/Modelfile
ollama run namo-lora
```

---

## Directory Structure

```
tools/lora/
├── config.py           All hyperparameters
├── prepare_data.py     Build training JSONL from Tripitaka corpus
├── train.py            QLoRA fine-tuning (PEFT + TRL SFTTrainer)
├── evaluate.py         Reference prompts, ROUGE, interactive eval
├── export_model.py     Merge adapter → HF model → GGUF
├── requirements.txt    Python dependencies
├── checkpoints/        Training output (created at runtime)
│   └── final_adapter/  Best adapter weights
├── merged/             Merged HF model (created by export_model.py)
└── merged-gguf/        GGUF + Modelfile (created by export_model.py)

knowledge/lora/         Training data (created by prepare_data.py)
├── train.jsonl
├── val.jsonl
└── stats.json
```

---

## Training Data Format

Each line in `train.jsonl` uses the LLaMA-3 instruction format:

```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{answer}<|eot_id|>
```

---

## Data Sources

| Source | Format | Examples |
|--------|--------|----------|
| `knowledge/global_library/book_XX_clean.json` | `{book, item_id, title, content}` | ~23 books × 3 templates/chunk |
| `knowledge/tripitaka_v25_curated.json` | `{topic, golden_sentence, curriculum_level}` | 7 curated sentences |
| `knowledge/classroom_mock_qa.json` | `{question, answer}` | 5 teacher-verified QA pairs |

Add more data by placing cleaned JSON books in `knowledge/global_library/`
and re-running `prepare_data.py`.

---

## Recommended Base Models

```python
# Thai-optimised (recommended)
base_model = "scb10x/llama-3-typhoon-v1.5-8b"

# Thai-first, lighter
base_model = "openthaigpt/openthaigpt1.5-7b-instruct"

# Multilingual baseline
base_model = "meta-llama/Llama-3.1-8B-Instruct"  # requires HF_TOKEN
```

---

## Prerequisite: batch_vectorizer.py

The full 168,861-vector Tripitaka FAISS index should be complete before
starting LoRA training — this ensures the RAG pipeline and LoRA model
train on the same canonical corpus version.

Check: `python scripts/audit_knowledge_vectors.py`
