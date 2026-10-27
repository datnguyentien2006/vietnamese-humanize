# Pipeline teacher LOCAL — toàn bộ chạy trên máy, 0 API (v1.3)

> Nguyên tắc đã chốt (26/10/2026): dự án **chỉ dùng cá nhân**, không phát hành
> tool/dataset → **giữ nguyên dữ liệu VietJack** trong corpus. Không dùng Groq
> hay bất kỳ API nào cho sinh dữ liệu, viết lại, hay đánh giá — mọi thứ chạy
> local trên máy (RTX 4050 6 GB VRAM / 16 GB RAM). Pipeline resume được, có
> backup, không ghi đè bản đang chạy cho đến khi bản mới qua test.

## 1. Model teacher đã chọn (sau benchmark)

| Model | Gate pass | fact_drift | s/call | tok/s | VRAM |
|---|---|---|---|---|---|
| **qwen3:4b-instruct-2507-q4_K_M** ✅ chọn | 4/8 | 3 | **5,7** | 59 | **3,1 GB** |
| qwen2.5:7b-instruct-q4_K_M | 4/8 | 2 | 9,7 | 28 | 4,1 GB |

Cả hai cho chất lượng tiếng Việt đạt gate như nhau trên mẫu benchmark; chọn
**qwen3:4b (Q4_K_M, 2,5 GB)** vì nhanh gấp đôi, rảnh VRAM. Report chi tiết:
`training/data/bench_local_report.md`. Chạy lại benchmark bất cứ lúc nào:

```powershell
.\.venv\Scripts\python.exe training\bench_local_teacher.py --models "qwen3:4b-instruct-2507-q4_K_M,qwen2.5:7b-instruct-q4_K_M"
```

## 2. Cài đặt một lần (Windows)

1. **Ollama** (đã cài 0.40.11): `C:\Users\USER\AppData\Local\Programs\Ollama\ollama.exe`
   — tải từ ollama.com/download, cài im lặng `OllamaSetup.exe /VERYSILENT`.
2. **Model**:
   ```powershell
   & "C:\Users\USER\AppData\Local\Programs\Ollama\ollama.exe" pull qwen3:4b-instruct-2507-q4_K_M
   ```
3. **Chạy server** (nếu chưa tự chạy — kiểm tra port 11434):
   ```powershell
   $env:OLLAMA_FLASH_ATTENTION='1'; $env:OLLAMA_CONTEXT_LENGTH='4096'
   & "C:\Users\USER\AppData\Local\Programs\Ollama\ollama.exe" serve
   ```

## 3. Chạy teacher trên toàn bộ corpus (resume được)

```powershell
Set-Location 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer'
$env:TEACHER_API_BASE = 'http://127.0.0.1:11434/v1'
$env:TEACHER_MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
$env:TEACHER_API_KEY = 'local'
$env:TEACHER_TIMEOUT_SECONDS = '300'
.\.venv\Scripts\python.exe training\prepare_dataset.py --mode synthesize --dirtying llm --source training/data/raw_staged --out-dir training/data/sft_v2
```

- **Tốc độ thực đo:** ~6,8 call/phút (GPU 95%, 3,1 GB VRAM) → toàn corpus
  3.679 tài liệu (~7,5 nghìn chunk) ≈ **18 giờ**. Chạy qua đêm.
- **Resume:** mọi output teacher ghi vào `training/data/sft/teacher_cache.jsonl`
  (append-only, key = sha1(severity|text)). Batch dừng giữa chừng (crash, mất
  điện, tắt máy) → **chạy lại đúng lệnh trên** là tiếp tục, không mất kết quả.
- **Không ghi đè:** output ghi vào `data/sft_v2/`; clobber-guard tự chuyển sang
  `sft_partial/` nếu batch mới nhỏ hơn bản đang có.
- Mỗi chunk cho tối đa 2 cặp: 1 biến thể LLM (theo chu kỳ L2/L2/L2/L3) + 1 biến
  thể rule L1 — Fact-token guard loại mọi output làm mất/sai số liệu.

## 4. Dựng dataset v2 (sau khi teacher chạy đủ)

```powershell
.\.venv\Scripts\python.exe training\build_mixed_from_cache.py --source training/data/raw_staged --out-dir training/data/sft_v2
```

- Ghép: rule pair cho MỌI chunk + LLM pair từ cache (không gọi lại model).
- Chạy lại bất cứ lúc nào để nâng độ phủ LLM; dataset chỉ lớn thêm.

## 5. QC local (không API)

```powershell
# Gate cơ khí toàn bộ:
.\.venv\Scripts\python.exe training\qc_judge.py --verify-only --sample 0
# LLM judge bằng chính model local:
.\.venv\Scripts\python.exe training\qc_judge.py --sample 150 --judges local:qwen3:4b-instruct-2507-q4_K_M
```

## 6. Backup — bản đồ phiên bản (KHÔNG xóa)

| Thư mục/file | Nội dung |
|---|---|
| `training/data/sft/` | **Bản đang chạy** (v1: 7.298 cặp mixed) |
| `training/data/sft_v0_rule_20261025/` | v0 — 3.226 cặp rule (backup) |
| `training/data/sft_v1_mixed_20261026/` | v1 — 7.298 cặp (backup) |
| `training/data/sft_v2/` | v2 — dataset local-teacher (đang dựng, ghi vào đây) |
| `training/data/sft_partial/` | nơi batch hỏng/nhỏ bị hướng tới (clobber-guard) |
| `training/data/upload_corpus_v1.zip`, `upload_sft_v1.zip` | gói upload Kaggle/Colab |
| `training/data/raw/sources.jsonl` + `_provenance.jsonl` mỗi nguồn | provenance từng tài liệu |

Quy tắc: `sft_v2` chỉ được thay thế `sft` (đổi tên thư mục) sau khi
verify-only QC pass ≥ 99% và đọc manifest không có `fact_drift`.

## 7. Dữ liệu VietJack

44 bài văn mẫu (33.682 từ) trong `training/data/raw/own/` — **giữ nguyên**,
provenance ghi nguồn + "chỉ dùng nghiên cứu nội bộ" (dự án cá nhân, không phát
hành). Không có lý do gì phải loại khỏi dataset.

## 8. Sự cố thường gặp

| Triệu chứng | Xử lý |
|---|---|
| Ollama không phản hồi | Kiểm tra port 11434; chạy lại `ollama serve`; chạy lại batch (cache giữ kết quả) |
| VRAM đầy / chậm | Đóng app chiếm GPU; hoặc dùng `qwen2.5:3b-instruct-q4_K_M`; hoặc giảm `OLLAMA_CONTEXT_LENGTH` |
| Muốn đổi teacher | Benchmark model mới rồi đặt `TEACHER_MODEL` — cache cũ vẫn hợp lệ (key theo severity+text) |
| Batch teacher dở dang | Chạy lại đúng lệnh — tự tiếp tục từ cache |

---

## 9. Serving local bằng Ollama (ĐÃ CHẠY THÀNH CÔNG — 28/10/2026)

Model đã train trên Kaggle (7B, 412 steps) → export GGUF Q4_K_M → import vào Ollama.

```powershell
# 1) Bật Ollama với cấu hình tối ưu cho GPU 6 GB (KV cache q8_0 → chạy 84% GPU, 29 tok/s)
$env:OLLAMA_KEEP_ALIVE='-1'; $env:OLLAMA_NUM_PARALLEL='1'; $env:OLLAMA_MAX_LOADED_MODELS='1'
$env:OLLAMA_FLASH_ATTENTION='1'; $env:OLLAMA_CONTEXT_LENGTH='4096'; $env:OLLAMA_KV_CACHE_TYPE='q8_0'
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve

# 2) Import model (chạy trong thư mục có Modelfile + file GGUF)
Set-Location training\output\kaggle_export
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" create humanizer-vi -f Modelfile

# 3) Trỏ backend về model local (đã cấu hình sẵn trong web/backend/.env)
#    HUMANIZER_API_BASE=http://127.0.0.1:11434/v1
#    HUMANIZER_MODEL=humanizer-vi
#    HUMANIZER_API_KEY=local
python training\doctor.py     # phải in: provider dự kiến: humanizer-model

# 4) Chạy backend + frontend
cd web\backend; ..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
cd web\frontend; npm run dev
```

**Kết quả đo thực tế:** 29,1 tok/s · 8,2 giây/đoạn 3 câu · fact_check 0 mất số liệu ·
`provider: humanizer-model`.

**Giới hạn cần biết:** `num_ctx 4096` → văn bản dài quá ~1.500 từ nên chia nhỏ trước khi
humanize (nếu vượt, backend sẽ báo lỗi fact-check hoặc rơi về Groq fallback).

**Sự cố thường gặp:**
| Triệu chứng | Xử lý |
|---|---|
| Model trả lời chậm bất thường (>30s/đoạn) | `ollama ps` xem cột PROCESSOR; nếu CPU > 30% → giảm `num_ctx` xuống 2048 trong Modelfile rồi `ollama create` lại |
| `Error: ... command must be one of` khi create | Modelfile dùng `PARAMETER stop` (không phải `STOP`) |
| Output bị cắt cụt | tăng `PARAMETER num_ctx` hoặc chia nhỏ văn bản đầu vào |
