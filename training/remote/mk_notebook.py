# -*- coding: utf-8 -*-
"""Generate training/remote/humanizer_colab.ipynb + kaggle kernel metadata.

Run once (locally or in Colab):  python training/remote/mk_notebook.py
Output: a GPU-ready notebook that works on Google Colab and Kaggle alike,
plus the package description for `kaggle kernels push`.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPO_URL = "https://github.com/datnguyentien2006/vietnamese-humanize.git"
OUT_DIR = REPO / "training" / "remote"


def cell(kind: str, source: str) -> dict:
    base: dict = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        base["execution_count"] = None
        base["outputs"] = []
    return base


cells = [
    cell(
        "markdown",
        """# Fine-tune the Vietnamese humanizer (QLoRA, T4-class)

Train on **Colab or Kaggle free GPU (T4/P100, 16 GB)**. Five cells, run top to bottom:

1. GPU check + clone repo + install deps
2. Point at the human-written corpus
3. Build the SFT dataset (`prepare_dataset.py`)
4. Train QLoRA (`train_qlora.py`; auto-falls back to 7B if the 14B OOMs)
5. Merge the adapter + optional AWQ export; persist artifacts

Edit the CONFIG cell once. Regenerate this notebook by editing
`training/remote/mk_notebook.py` — the notebook itself is disposable.""",
    ),
    cell(
        "code",
        f"""# ==== 0. CONFIG ====
REPO_URL = "{REPO_URL}"
DATA_RAW = None            # Colab: r"/content/drive/MyDrive/vietnamese-humanize/data-raw" (a folder of .txt/.txt.gz/.jsonl/.parquet corpora)
                           # Kaggle: leave None and attach ONE dataset with the text corpus — auto-detected
PERSIST_DIR = None         # Colab: r"/content/drive/MyDrive/vietnamese-humanize/out" ; on Kaggle outputs are kept automatically (kernel output)
TRAIN_MODEL = None         # None -> use training/config.yaml (14B base). Set 'Qwen/Qwen2.5-7B-Instruct' to force fallback.
LIMIT = None               # None -> all corpus docs; e.g. 20000 for a quick dry run
RUN_AWQ_EXPORT = True""",
    ),
    cell(
        "code",
        """# ==== 1. GPU check + clone + install ====
!nvidia-smi

import os, subprocess

if not os.path.isdir("vietnamese-humanize/.git"):
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, "vietnamese-humanize"], check=True)
%cd vietnamese-humanize

!pip install -q -r training/requirements.txt
!pip install -q huggingface_hub
print("setup ok")""",
    ),
    cell(
        "code",
        """# ==== 2. Corpus ====
# Chooses, in order: Kaggle attached dataset -> Colab Drive folder -> Colab prompt mount.

import glob, os, shutil


def use_corpus_from(source: str) -> None:
    if os.path.islink("training/data/raw"):
        os.remove("training/data/raw")
    elif os.path.isdir("training/data/raw"):
        shutil.rmtree("training/data/raw")
    os.makedirs("training/data", exist_ok=True)
    os.symlink(source, "training/data/raw")
    files = sorted(glob.glob(source + "*"))[:10]
    print("linked:", source)
    print("sample files:", files)


kaggle_inputs = sorted(glob.glob("/kaggle/input/*"))
if kaggle_inputs:
    use_corpus_from(kaggle_inputs[0])            # one dataset = the corpus
elif DATA_RAW:
    use_corpus_from(DATA_RAW)
else:
    from google.colab import drive
    drive.mount("/content/drive")
    use_corpus_from(input("Thư mục corpus (người viết) trong Drive: "))
print("corpus ok")""",
    ),
    cell(
        "code",
        """# ==== 3. Build SFT dataset ====
limit_arg = "" if LIMIT is None else f"--limit {LIMIT}"
!python training/prepare_dataset.py {limit_arg}
with open("training/data/sft/train.jsonl", encoding="utf-8") as fh:
    print(fh.read(700))""",
    ),
    cell(
        "code",
        """# ==== 4. Train QLoRA (14B, falls back to 7B on OOM) ====
import subprocess

FALLBACK = "Qwen/Qwen2.5-7B-Instruct"


def try_train(model_id):
    cmd = ["python", "training/train_qlora.py"]
    if model_id:
        cmd += ["--model", model_id]
    print("RUN:", *cmd)
    proc = subprocess.run(cmd)
    print("exit code:", proc.returncode)
    return proc.returncode == 0


ok = try_train(TRAIN_MODEL)
if not ok and TRAIN_MODEL != FALLBACK:
    print("[warn] falling back to", FALLBACK)
    ok = try_train(FALLBACK)
assert ok, "Training failed on both 14B and 7B — lower LIMIT or free disk/VRAM, then retry."
print("adapter: training/output/humanizer-lora")""",
    ),
    cell(
        "code",
        """# ==== 5. Merge + AWQ export + persist ====
import os, shutil

if RUN_AWQ_EXPORT:
    !python training/merge_and_export.py --export-awq
else:
    !python training/merge_and_export.py

if PERSIST_DIR:
    os.makedirs(PERSIST_DIR, exist_ok=True)
    for kind in ("lora", "merged", "awq"):
        src = f"training/output/humanizer-{kind}"
        dst = os.path.join(PERSIST_DIR, f"humanizer-{kind}")
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print("persisted:", dst)
else:
    print("artifacts remain in training/output/* for this session (download manually on Colab)")
print("DONE")""",
    ),
]

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "humanizer_colab.ipynb").write_text(
    json.dumps(
        {
            "nbformat": 4,
            "nbformat_minor": 0,
            "metadata": {
                "colab": {"provenance": []},
                "accelerator": "GPU",
                "kaggle": {"accelerator": "nvidiaTeslaT4"},
                "language_info": {"name": "python"},
            },
            "cells": cells,
        },
        ensure_ascii=False,
        indent=1,
    ),
    encoding="utf-8",
)

(OUT_DIR / "kernel-metadata.json").write_text(
    json.dumps(
        {
            "id": "PUT_YOUR_KAGGLE_USERNAME/humanizer-vi-train",
            "code_file": "humanizer_colab.ipynb",
            "language_type": "notebook",
            "id_is_slug": False,
            "is_private": True,
            "enable_gpu": True,
            "enable_tpu": False,
            "enable_internet": True,
            "dataset_sources": [],
            "kernel_sources": [],
            "competition_sources": [],
            "model_sources": [],
        },
        indent=2,
    ),
    encoding="utf-8",
)

print("wrote:", (OUT_DIR / "humanizer_colab.ipynb").as_posix())
print("wrote:", (OUT_DIR / "kernel-metadata.json").as_posix())
