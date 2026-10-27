# -*- coding: utf-8 -*-
"""Export humanizer adapter -> GGUF Q4_K_M (chạy trên Kaggle T4).

Vì sao có kernel này: notebook train chính bị giới hạn session 9 giờ, merge/AWQ
bị cắt trước khi xong. Kernel này chỉ làm phần export, dùng adapter đã train:

  adapter (kernel humanizer-vi-train) -> merge fp16 -> GGUF f16 -> Q4_K_M (~4.4 GB)

Ra: /kaggle/working/humanizer-7b-Q4_K_M.gguf + Modelfile (chạy Ollama trên máy 6 GB).

kernel_sources: ["mytham/humanizer-vi-train"]  (adapter nằm trong output kernel đó)
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

BASE_ID = "Qwen/Qwen2.5-7B-Instruct"
WORK = "/kaggle/working"
TMP = "/tmp"
MERGED = f"{TMP}/merged"
GGUF_F16 = f"{TMP}/model-f16.gguf"
GGUF_Q4 = f"{WORK}/humanizer-7b-Q4_K_M.gguf"


def run(cmd: list[str], **kw) -> None:
    check = kw.pop("check", True)
    print("RUN:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=check, **kw)


def main() -> int:
    # 1. Tìm adapter trong output kernel trước
    hits = glob.glob("/kaggle/input/**/humanizer-lora", recursive=True)
    if not hits:
        hits = glob.glob("/kaggle/input/**/adapter_model.safetensors", recursive=True)
        hits = [os.path.dirname(h) for h in hits]
    assert hits, "Không tìm thấy adapter trong /kaggle/input"
    adapter = hits[0]
    print("adapter:", adapter, flush=True)

    # 2. Cài dependency
    run([sys.executable, "-m", "pip", "install", "-q",
         "transformers>=4.46", "accelerate>=1.0", "peft>=0.14",
         "sentencepiece", "protobuf", "gguf"])
    # Kaggle cài sẵn torchao 0.10 nhưng peft mới yêu cầu >0.16 → ImportError khi
    # PeftModel khởi tạo. Gỡ torchao: peft coi như "không có" và bỏ qua nhánh đó.
    run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], check=False)

    # 3. Merge adapter vào base (fp16 trên GPU T4 16 GB)
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print("[merge] load base fp16 -> GPU", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_ID, torch_dtype=torch.float16, device_map={"": 0}, low_cpu_mem_usage=True
    )
    model = PeftModel.from_pretrained(model, adapter)
    model = model.merge_and_unload()
    model.save_pretrained(MERGED, safe_serialization=True)
    AutoTokenizer.from_pretrained(adapter).save_pretrained(MERGED)
    del model
    torch.cuda.empty_cache()
    print("[merge] xong ->", MERGED, flush=True)

    # 4. llama.cpp (convert script + quantize binary)
    run(["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp", f"{TMP}/llama.cpp"])
    run([sys.executable, "-m", "pip", "install", "-q", "-r", f"{TMP}/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt"])

    api = urllib.request.Request(
        "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest",
        headers={"User-Agent": "humanizer-export"},
    )
    with urllib.request.urlopen(api, timeout=60) as resp:
        release = json.loads(resp.read().decode())
    asset_url = next(
        (a["browser_download_url"] for a in release["assets"] if "bin-ubuntu-x64" in a["name"]),
        None,
    )
    quant_bin = None
    quant_libdir = None
    if asset_url:
        print("quantize binary:", asset_url, flush=True)
        zip_path = f"{TMP}/llama-bin.zip"
        urllib.request.urlretrieve(asset_url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(f"{TMP}/llama-bin")
        found = glob.glob(f"{TMP}/llama-bin/**/llama-quantize", recursive=True)
        assert found, "không thấy llama-quantize trong zip"
        # Giữ nguyên chỗ: binary cần các libggml*.so cùng thư mục (LD_LIBRARY_PATH).
        quant_bin = found[0]
        quant_libdir = os.path.dirname(quant_bin)
        os.chmod(quant_bin, 0o755)
    else:  # dự phòng: tự build
        run(["cmake", "-B", f"{TMP}/build", "-S", f"{TMP}/llama.cpp", "-DLLAMA_CURL=OFF"])
        run(["cmake", "--build", f"{TMP}/build", "--target", "llama-quantize", "-j4"])
        quant_bin = f"{TMP}/build/bin/llama-quantize"
        quant_libdir = os.path.dirname(quant_bin)
        os.chmod(quant_bin, 0o755)

    # 5. Convert fp16 -> GGUF f16 -> Q4_K_M
    run([sys.executable, f"{TMP}/llama.cpp/convert_hf_to_gguf.py", MERGED,
         "--outfile", GGUF_F16, "--outtype", "f16"])
    quant_env = dict(os.environ)
    if quant_libdir:
        quant_env["LD_LIBRARY_PATH"] = quant_libdir + ":" + quant_env.get("LD_LIBRARY_PATH", "")
    run([quant_bin, GGUF_F16, GGUF_Q4, "Q4_K_M"], cwd=WORK, env=quant_env)

    # 6. Modelfile cho Ollama (chat template Qwen2.5) + dọn /tmp
    modelfile = '''FROM ./humanizer-7b-Q4_K_M.gguf

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.05
PARAMETER num_ctx 4096

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""
STOP "<|im_end|>"
'''
    with open(f"{WORK}/Modelfile", "w", encoding="utf-8") as fh:
        fh.write(modelfile)
    shutil.rmtree(MERGED, ignore_errors=True)
    for p in (GGUF_F16, f"{TMP}/llama.cpp", f"{TMP}/llama-bin", f"{TMP}/llama-bin.zip"):
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p):
            os.remove(p)

    size_gb = os.path.getsize(GGUF_Q4) / 1e9
    print(f"GGUF_Q4: {size_gb:.2f} GB -> {GGUF_Q4}", flush=True)
    print("EXPORT_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
