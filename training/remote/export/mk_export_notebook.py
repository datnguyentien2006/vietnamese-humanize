# -*- coding: utf-8 -*-
"""Sinh notebook export GGUF (log stream realtime) + kernel metadata.

Kaggle KHÔNG stream log cho kernel dạng script (log câm cho tới khi job đóng)
— đổi sang notebook để thấy tiến trình từng cell. Chạy: python mk_export_notebook.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def cell(kind: str, src: str) -> dict:
    base = {"cell_type": kind, "metadata": {}, "source": src.splitlines(keepends=True)}
    if kind == "code":
        base["execution_count"] = None
        base["outputs"] = []
    return base


cells = [
    cell(
        "markdown",
        """# Export humanizer adapter → GGUF Q4_K_M

Merge adapter (từ kernel `humanizer-vi-train`) vào base Qwen2.5-7B-Instruct rồi
quantize Q4_K_M (~4,4 GB) để chạy Ollama trên GPU 6 GB.

**5 cell, chạy từ trên xuống** — mỗi cell in tiến trình nên Logs hiện realtime.
Đầu ra cuối cùng: `humanizer-7b-Q4_K_M.gguf` + `Modelfile` trong `/kaggle/working`.""",
    ),
    cell(
        "code",
        """# ==== 1. Cài đặt + tìm adapter ====
# Ghim transformers < 5: bản 5.x đổi API tokenizer làm convert_hf_to_gguf.py
# của llama.cpp vỡ (AttributeError: 'list' object has no attribute 'keys').
!pip install -q "transformers>=4.46,<5" "tokenizers<0.22" "accelerate>=1.0,<2" "peft>=0.14" sentencepiece protobuf gguf psutil
# Kaggle có sẵn torchao 0.10 nhưng peft mới cần >0.16 -> gỡ để peft bỏ qua nhánh đó
!pip uninstall -y -q torchao

import glob, os, torch, peft, transformers
print("torch:", torch.__version__, "| transformers:", transformers.__version__, "| peft:", peft.__version__)
print("cuda:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")

hits = glob.glob("/kaggle/input/**/humanizer-lora", recursive=True)
assert hits, "Không tìm thấy humanizer-lora trong /kaggle/input"
ADAPTER = hits[0]
print("adapter:", ADAPTER)
print("files:", sorted(os.listdir(ADAPTER)))""",
    ),
    cell(
        "code",
        """# ==== 2. Merge adapter vào base (fp16 trên CPU — T4 14.5 GB không đủ chứa 7B fp16) ====
import gc, os, shutil, time
import psutil, torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_ID = "Qwen/Qwen2.5-7B-Instruct"
MERGED = "/tmp/merged"
shutil.rmtree(MERGED, ignore_errors=True)
print(f"RAM: {psutil.virtual_memory().total/1e9:.1f} GB · còn trống {psutil.virtual_memory().available/1e9:.1f} GB", flush=True)

t0 = time.time()
print("[1/3] tải + nạp base fp16 lên CPU (14,5 GB, 3-8 phút) ...", flush=True)
model = AutoModelForCausalLM.from_pretrained(
    BASE_ID, torch_dtype=torch.float16, device_map="cpu", low_cpu_mem_usage=True
)
print(f"      xong sau {time.time()-t0:.0f}s · RAM dùng {psutil.Process().memory_info().rss/1e9:.1f} GB", flush=True)

print("[2/3] gắn + merge LoRA ...", flush=True)
model = PeftModel.from_pretrained(model, ADAPTER).merge_and_unload()
print(f"      xong sau {time.time()-t0:.0f}s", flush=True)

print("[3/3] ghi /tmp/merged (15 GB, 3-6 phút) ...", flush=True)
model.save_pretrained(MERGED, safe_serialization=True)
# Tokenizer phải lấy từ BASE (adapter chỉ có tokenizer.json rút gọn → convert GGUF
# đòi tokenizer.model/tokenizer.json đầy đủ, thiếu là FileNotFoundError).
AutoTokenizer.from_pretrained(BASE_ID, trust_remote_code=True).save_pretrained(MERGED)
del model
gc.collect()
size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(MERGED) for f in fs)
print(f"[merge] xong toàn bộ sau {time.time()-t0:.0f}s · {size/1e9:.1f} GB -> {MERGED}", flush=True)
print("tokenizer files:", sorted(f for f in os.listdir(MERGED) if 'token' in f or f.endswith('.model')), flush=True)""",
    ),
    cell(
        "code",
        """# ==== 3. llama.cpp: convert fp16 -> GGUF f16 (15 GB) ====
import glob, os, subprocess, sys, time

TMP = "/tmp"
GGUF_F16 = f"{TMP}/model-f16.gguf"

if not os.path.isdir(f"{TMP}/llama.cpp"):
    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/ggml-org/llama.cpp", f"{TMP}/llama.cpp"], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                f"{TMP}/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt"], check=True)

t0 = time.time()
print("[convert] bắt đầu (15 GB, thường 10-25 phút) ...", flush=True)
subprocess.run([sys.executable, f"{TMP}/llama.cpp/convert_hf_to_gguf.py", "/tmp/merged",
                "--outfile", GGUF_F16, "--outtype", "f16"], check=True)
print(f"[convert] xong sau {time.time()-t0:.0f}s · {os.path.getsize(GGUF_F16)/1e9:.1f} GB", flush=True)""",
    ),
    cell(
        "code",
        """# ==== 4. Quantize Q4_K_M + Modelfile Ollama + dọn /tmp ====
import glob, json, os, shutil, subprocess, urllib.request, zipfile

TMP = "/tmp"
WORK = "/kaggle/working"
GGUF_F16 = f"{TMP}/model-f16.gguf"
GGUF_Q4 = f"{WORK}/humanizer-7b-Q4_K_M.gguf"

api = urllib.request.Request(
    "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest",
    headers={"User-Agent": "humanizer-export"},
)
with urllib.request.urlopen(api, timeout=60) as resp:
    release = json.loads(resp.read().decode())
asset = next((a["browser_download_url"] for a in release["assets"] if "bin-ubuntu-x64" in a["name"]), None)
env = dict(os.environ)
if asset:
    print("quantize binary:", asset, flush=True)
    urllib.request.urlretrieve(asset, f"{TMP}/llama-bin.zip")
    with zipfile.ZipFile(f"{TMP}/llama-bin.zip") as zf:
        zf.extractall(f"{TMP}/llama-bin")
    qbin = glob.glob(f"{TMP}/llama-bin/**/llama-quantize", recursive=True)[0]
    os.chmod(qbin, 0o755)
    env["LD_LIBRARY_PATH"] = os.path.dirname(qbin) + ":" + env.get("LD_LIBRARY_PATH", "")
else:
    subprocess.run(["cmake", "-B", f"{TMP}/build", "-S", f"{TMP}/llama.cpp", "-DLLAMA_CURL=OFF"], check=True)
    subprocess.run(["cmake", "--build", f"{TMP}/build", "--target", "llama-quantize", "-j4"], check=True)
    qbin = f"{TMP}/build/bin/llama-quantize"

print("[quantize] bắt đầu (5-15 phút) ...", flush=True)
subprocess.run([qbin, GGUF_F16, GGUF_Q4, "Q4_K_M"], cwd=WORK, check=True, env=env)

with open(f"{WORK}/Modelfile", "w", encoding="utf-8") as fh:
    chat = ('{{ if .System }}<|im_start|>system\\n'
            '{{ .System }}<|im_end|>\\n'
            '{{ end }}<|im_start|>user\\n'
            '{{ .Prompt }}<|im_end|>\\n'
            '<|im_start|>assistant\\n')
    fh.write("\\n".join([
        "FROM ./humanizer-7b-Q4_K_M.gguf",
        "",
        "PARAMETER temperature 0.7",
        "PARAMETER top_p 0.9",
        "PARAMETER repeat_penalty 1.05",
        "PARAMETER num_ctx 4096",
        "",
        'TEMPLATE """' + chat + '"""',
        'STOP "<|im_end|>"',
        "",
    ]))

for p in ("/tmp/merged", "/tmp/llama.cpp", "/tmp/llama-bin"):
    shutil.rmtree(p, ignore_errors=True)
for p in (GGUF_F16, "/tmp/llama-bin.zip"):
    if os.path.isfile(p):
        os.remove(p)

print(f"GGUF_Q4: {os.path.getsize(GGUF_Q4)/1e9:.2f} GB -> {GGUF_Q4}", flush=True)
print("EXPORT_DONE", flush=True)""",
    ),
]

notebook = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {"provenance": []},
        "accelerator": "GPU",
        "kaggle": {"accelerator": "nvidiaTeslaT4"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "cells": cells,
}

(OUT / "export_gguf.ipynb").write_text(
    json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8"
)

metadata = {
    "id": "mytham/humanizer-vi-export",
    "title": "humanizer-vi-export",
    "code_file": "export_gguf.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    # Merge chạy trên CPU (T4 14.5 GB không chứa nổi 7B fp16) → không cần GPU,
    # tránh luôn giới hạn 2 phiên GPU đồng thời của Kaggle.
    "enable_gpu": False,
    "enable_tpu": False,
    "enable_internet": True,
    "dataset_sources": [],
    "kernel_sources": ["mytham/humanizer-vi-train"],
    "competition_sources": [],
    "model_sources": [],
}
(OUT / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print("wrote:", (OUT / "export_gguf.ipynb").as_posix())
print("wrote:", (OUT / "kernel-metadata.json").as_posix())
