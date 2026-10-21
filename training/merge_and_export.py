# -*- coding: utf-8 -*-
"""Merge the fine-tuned LoRA adapter into the base model and export weights.

Steps:
  1. merge: load the full base checkpoint in bf16/fp16, load the LoRA adapter
     produced by train_qlora.py, merge it into the base weights, and save the
     full model to training/output/humanizer-merged/.
  2. --export-awq (optional): quantize the merged model with AutoAWQ into an
     AWQ checkpoint, the format served by the self-hosted vLLM endpoint.
     This step needs a CUDA GPU (works on a T4, ~20-40 minutes for 14B).

Run on a machine with enough free disk: the merged 14B model is ~28 GB, the
AWQ export is ~10 GB. On Colab, output to Google Drive.

Usage:
  python training/merge_and_export.py
  python training/merge_and_export.py --export-awq
  python training/merge_and_export.py --awq-only --merged-dir /content/drive/...
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with (ROOT / "training" / "config.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def resolve(path_value: str, override: str | None) -> Path:
    return Path(ROOT / (override or path_value))


def merge(config: dict, merged_dir: Path, model_override: str | None) -> None:
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = model_override or config["model"]["training_model_id"]
    adapter_dir = Path(config["output"]["adapter_dir"])
    if merged_dir.exists() and any(merged_dir.iterdir()):
        print(f"[skip] merged model tồn tại sẵn: {merged_dir.as_posix()}")
        return

    print(f"[load] base: {model_id} (fp16, merge LoRA không quantize)")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    print(f"[load] adapter: {adapter_dir.as_posix()}")
    model = PeftModel.from_pretrained(model, adapter_dir)
    model = model.merge_and_unload()
    merged_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(merged_dir, safe_serialization=True)
    tokenizer.save_pretrained(merged_dir)
    print(f"[done] merged model: {merged_dir.as_posix()} (~28 GB cho 14B)")
    print("[next ] đẩy merged model lên một repo HuggingFace riêng, dùng vLLM để serve")


def export_awq(merged_dir: Path, awq_dir: Path) -> None:
    from awq import AutoAWQForCausalLM

    awq_dir.parent.mkdir(parents=True, exist_ok=True)
    print(f"[awq  ] quantize: {merged_dir.as_posix()} -> {awq_dir.as_posix()}")
    model = AutoAWQForCausalLM.from_pretrained(str(merged_dir), device_map="cuda")
    tokenizer = AutoTokenizer.from_pretrained(str(merged_dir), trust_remote_code=True)
    quantization_config = {
        "zero_point": True,
        "q_group_size": 128,
        "w_bit": 4,
        "version": "GEMM",
    }
    model.quantize(tokenizer, quant_config=quantization_config)
    model.save_quantized(str(awq_dir))
    tokenizer.save_pretrained(str(awq_dir))
    print(f"[done ] AWQ export: {awq_dir.as_posix()} (~10 GB cho 14B)")
    print("[next ] serve bằng vLLM — xem training/serve/runpod_vllm.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-awq", action="store_true", help="after merge, quantize to AWQ")
    parser.add_argument(
        "--awq-only", action="store_true", help="expect merged model already saved, skip merge"
    )
    parser.add_argument("--merged-dir", help="override merged output dir (vd: Google Drive)")
    parser.add_argument("--model", help="override base checkpoint id used for the merge")
    args = parser.parse_args()

    config = load_config()
    merged_dir = resolve(config["output"]["merged_dir"], args.merged_dir)
    awq_dir = Path(config["output"]["awq_dir"])
    awq_dir.parent.mkdir(parents=True, exist_ok=True)
    if args.merged_dir:
        awq_dir = awq_dir.parent / "humanizer-awq"

    if args.awq_only:
        if not merged_dir.exists():
            raise SystemExit(f"merged model chưa có: {merged_dir.as_posix()}")
        export_awq(merged_dir, awq_dir)
        return

    merge(config, merged_dir, args.model)
    if args.export_awq:
        export_awq(merged_dir, awq_dir)


if __name__ == "__main__":
    main()
