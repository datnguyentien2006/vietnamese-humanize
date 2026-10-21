# Serving the humanizer model — self-hosted vLLM

Goal: expose the fine-tuned checkpoint as an OpenAI-compatible HTTP endpoint
(`POST /v1/chat/completions`) that the web backend will call instead of Groq.

## 1. Publish the checkpoint

Directly after `merge_and_export.py`:

1. Create a **private** HuggingFace repo, e.g. `datnguyentien2006/humanizer-vi-awq`.
2. Upload the AWQ export (`training/output/humanizer-awq/`), not the 28 GB
   merged folder — AWQ is ~10 GB and enough for serving.
3. (Recommended) push the LoRA adapter folder too, so you can re-merge
   without retraining.

```bash
pip install huggingface_hub
huggingface-cli login
huggingface-cli upload datnguyentien2006/humanizer-vi-awq training/output/humanizer-awq .
```

## 2. Run vLLM

Works on Runpod, Vast.ai, your own GPU box, or any host with ≥16 GB VRAM
(14B AWQ ≈ 10 GB weights + KV cache).

```bash
pip install vllm
export HF_TOKEN=hf_....             # nếu repo để private
vllm serve datnguyentien2006/humanizer-vi-awq \
  --served-model-name humanizer-vi \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --api-key <một-secret-tự-chọn>
```

Check it works:

```bash
curl -X POST http://<host>:8000/v1/chat/completions \
  -H "Content-Type: application/json" -H "Authorization: Bearer <secret>" \
  -d '{
    "model": "humanizer-vi",
    "temperature": 0.5,
    "messages": [
      {"role": "system", "content": "<paste SYSTEM_PROMPT từ training/task_prompts.py>"},
      {"role": "user", "content": "<paste USER_TEMPLATE với <ORIGINAL>…</ORIGINAL>>"}
    ]
  }'
```

Runpod notes:

- Template: `runpod/pytorch` with CUDA 12+; expose port 8000 publicly.
- Disk ≥ 30 GB so the checkpoint can download into `/root/.cache/huggingface`.
- vLLM keeps the model resident in VRAM: use a persistent pod, or accept cold
  starts (a few minutes) on serverless/spot instances.

## 3. Backend contract (khi gắn vào web app)

The backend rewrite service will switch from Groq to this endpoint with
environment variables only (no provider SDK):

| Env var | Mô tả |
| --- | --- |
| `HUMANIZER_API_BASE` | `https://<host>:8000/v1` |
| `HUMANIZER_API_KEY` | API key của endpoint |
| `HUMANIZER_MODEL` | `humanizer-vi` (`--served-model-name`) |

Integration requirements when the swap happens:

1. Reuse `training/task_prompts.py` verbatim — prompt must match the training
   template exactly (`<ORIGINAL>…</ORIGINAL>` tags), otherwise quality drops.
2. Validate the response against the original text: same set of numbers,
   dates, proper names must survive; otherwise fall back and retry once.
3. Keep the manual edit + compare UI as-is: the user always reviews and can
   edit the rewrite.
4. Keep `GROQ_API_KEY` as an optional fallback provider flag until the own
   model reaches parity in the review checklist.

## 4. Cost / scale checklist

- Start with a single GPU pod for testing; scale only after the review UI
  confirms latency acceptable (< ~20 s for a 400-word paragraph on T4-class;
  A10/24 GB easily a few seconds).
- vLLM keeps the model resident: mark the pod **persistent**, use spot
  instances only if you accept cold starts.
