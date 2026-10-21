# -*- coding: utf-8 -*-
"""QLoRA fine-tune of a Vietnamese-capable instruct model for text humanization.

Pipeline:
  1. prepare_dataset.py writes training/data/sft/{train,val}.jsonl (chat format).
  2. This script loads the base model in 4-bit (bitsandbytes NF4), trains LoRA
     adapters with TRL SFTTrainer, and saves the adapter to training/output/.
  3. merge_and_export.py merges the adapter and exports the serving checkpoint.

Designed for a free Colab/Kaggle T4 (16 GB). If the 14B base runs out of
memory, rerun with:
    python training/train_qlora.py --model Qwen/Qwen2.5-7B-Instruct

Note: AWQ checkpoints (Qwen/Qwen2.5-14B-Instruct-AWQ) cannot be QLoRA-trained;
training always uses the full checkpoint, the AWQ variant is produced at
export time for the self-hosted vLLM endpoint.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
import yaml
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with (ROOT / "training" / "config.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="base checkpoint id; defaults to config.yaml")
    parser.add_argument("--seq-len", type=int)
    parser.add_argument("--epochs", type=float)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--grad-accum", type=int)
    args = parser.parse_args()

    cfg = load_config()
    train_cfg = dict(cfg["train"])
    model_id = args.model or cfg["model"]["training_model_id"]
    if args.seq_len:
        train_cfg["seq_len"] = args.seq_len
    if args.epochs:
        train_cfg["epochs"] = args.epochs
    if args.batch_size:
        train_cfg["per_device_batch_size"] = args.batch_size
    if args.grad_accum:
        train_cfg["grad_accumulation"] = args.grad_accum
    if args.model:
        print(f"[info] base model được chỉ định tay: {model_id}")

    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    compute_dtype = torch.float16 if train_cfg["fp16"] else torch.bfloat16
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    print(f"[load] base model: {model_id}")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=train_cfg["gradient_checkpointing"],
    )
    lora_config = LoraConfig(
        r=cfg["lora"]["r"],
        lora_alpha=cfg["lora"]["alpha"],
        lora_dropout=cfg["lora"]["dropout"],
        bias=cfg["lora"]["bias"],
        target_modules=cfg["lora"]["target_modules"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = load_dataset(
        "json",
        data_files={
            "train": str(ROOT / "training" / "data" / "sft" / "train.jsonl"),
            "val": str(ROOT / "training" / "data" / "sft" / "val.jsonl"),
        },
    )
    dataset = dataset.map(
        lambda ex: {
            "text": tokenizer.apply_chat_template(
                ex["messages"], tokenize=False, add_generation_prompt=False
            )
        },
        remove_columns=dataset["train"].column_names,
    )

    # trl renamed max_seq_length -> max_length in recent releases; keep compat.
    try:
        sft_config = SFTConfig(
            output_dir="training/output/checkpoints",
            max_seq_length=train_cfg["seq_len"],
            num_train_epochs=train_cfg["epochs"],
            learning_rate=train_cfg["lr"],
            optim="paged_adamw_8bit",
            per_device_train_batch_size=train_cfg["per_device_batch_size"],
            gradient_accumulation_steps=train_cfg["grad_accumulation"],
            warmup_ratio=train_cfg["warmup_ratio"],
            lr_scheduler_type=train_cfg["lr_scheduler"],
            fp16=train_cfg["fp16"],
            bf16=False,
            logging_steps=train_cfg["logging_steps"],
            eval_strategy="steps",
            eval_steps=0.2,
            save_strategy="steps",
            save_steps=0.5,
            save_total_limit=2,
            gradient_checkpointing=train_cfg["gradient_checkpointing"],
            max_grad_norm=0.3,
            report_to="none",
            dataset_num_proc=2,
        )
    except TypeError:
        # newer trl renamed max_seq_length -> max_length
        sft_config = SFTConfig(
            output_dir="training/output/checkpoints",
            max_length=train_cfg["seq_len"],
            num_train_epochs=train_cfg["epochs"],
            learning_rate=train_cfg["lr"],
            optim="paged_adamw_8bit",
            per_device_train_batch_size=train_cfg["per_device_batch_size"],
            gradient_accumulation_steps=train_cfg["grad_accumulation"],
            warmup_ratio=train_cfg["warmup_ratio"],
            lr_scheduler_type=train_cfg["lr_scheduler"],
            fp16=train_cfg["fp16"],
            bf16=False,
            logging_steps=train_cfg["logging_steps"],
            eval_strategy="steps",
            eval_steps=0.2,
            save_strategy="steps",
            save_steps=0.5,
            save_total_limit=2,
            gradient_checkpointing=train_cfg["gradient_checkpointing"],
            max_grad_norm=0.3,
            report_to="none",
            dataset_num_proc=2,
        )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset["train"],
        eval_dataset=dataset["val"],
        processing_class=tokenizer,
    )

    print("[train] bắt đầu fine-tune…")
    trainer.train()

    adapter_dir = ROOT / cfg["output"]["adapter_dir"]
    adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    print(f"[done] adapter đã lưu: {adapter_dir.as_posix()}")
    print("[next ] python training/merge_and_export.py --export-awq")


if __name__ == "__main__":
    main()
