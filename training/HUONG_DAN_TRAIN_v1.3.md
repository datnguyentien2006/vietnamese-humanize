# Hướng dẫn train vi-humanizer v1.3 — từ dataset đến serving

> Dataset v1 đã dựng xong tại `training/data/sft/` (7.298 cặp — 6.573 train / 725 val,
> 5 register, QC cơ khí 7.298/7.298 pass). File này là các bước còn lại.

## Tổng quan lộ trình còn lại

```
[Dataset v1 ✅] → [1. Train QLoRA trên Kaggle/Colab] → [2. Merge + AWQ] → [3. Serve vLLM] → [4. Bật HUMANIZER_API_BASE]
```

Máy bạn (RTX 4050, 6 GB VRAM) không đủ train 14B — dùng GPU miễn phí của
**Kaggle** (khuyến nghị: 9 giờ/session, 30 giờ/tuần) hoặc **Colab** T4.

## Chuẩn bị (15 phút, làm 1 lần)

1. Tải 2 file trong `training/data/`:
   - `upload_corpus_v1.zip` (12,6 MB — 3.679 tài liệu văn người, 6 nguồn)
   - `upload_sft_v1.zip` (5,4 MB — dataset đã dựng sẵn, dùng khi muốn bỏ qua bước build)
2. **Kaggle**: tạo tài khoản → Settings → API → *Create New Token* →
   đặt file tải về tại `%USERPROFILE%\.kaggle\kaggle.json`.

## Route A — Kaggle (khuyến nghị: không cần giữ tab, chạy ngầm)

1. **Upload corpus**: kaggle.com → *Datasets* → *New Dataset* → upload
   `upload_corpus_v1.zip` (giữ dạng zip, không cần giải nén — notebook tự xử lý)
   → đặt tên `vi-humanizer-corpus` (Private).
2. **Điền metadata**: mở `training/remote/kernel-metadata.json`:
   - `id`: `TÊN_KAGGLE_CỦA_BẠN/humanizer-vi-train`
   - `dataset_sources`: `["TÊN_KAGGLE_CỦA_BẠN/vi-humanizer-corpus"]`
3. **Push**:
   ```powershell
   pip install kaggle
   cd training\remote
   kaggle kernels push
   kaggle kernels status TÊN_BẠN/humanizer-vi-train   # kiểm tra định kỳ
   ```
4. Thời gian: build dataset ~20 phút + train 14B QLoRA ~5–8 giờ trên T4/P100.
   Nếu `CUDA OOM`, notebook tự rơi về **Qwen2.5-7B** (kém hơn chút, vẫn dùng được).
5. **Lấy kết quả**: khi status = COMPLETE:
   ```powershell
   kaggle kernels output TÊN_BẠN/humanizer-vi-train -p training\output\kaggle_run
   ```
   → bên trong có LoRA adapter đã merge + **bản AWQ** sẵn sàng serving.

## Route B — Colab (thay thế, cần giữ tab)

1. colab.research.google.com → *File → Upload notebook* → chọn
   `training/remote/humanizer_colab.ipynb` → *Runtime → Change runtime type → GPU T4*.
2. Upload `upload_corpus_v1.zip` lên Google Drive, giải nén vào một thư mục,
   sửa cell CONFIG: `DATA_RAW = r"/content/drive/MyDrive/vietnamese-humanize/data-raw"`
   và `PERSIST_DIR = r"/content/drive/MyDrive/vietnamese-humanize/out"`.
3. *Run all* (Ctrl+F9). Artifact (adapter + AWQ) nằm trong `PERSIST_DIR` trên Drive.
4. Colab free ngắt session sau vài giờ — nếu bị ngắt giữa chừng, mở lại và
   chạy tiếp từ cell train (checkpoint lưu trong Drive nếu PERSIST_DIR đã set).

## Sau khi train xong — serving (phần cuối của v1.3)

1. Adapter/AWQ về máy → nếu notebook đã xuất AWQ: dùng luôn; nếu chỉ có adapter:
   ```powershell
   python training/merge_and_export.py --export-awq
   ```
   (cần GPU có CUDA — làm trên chính session Kaggle/Colab trước khi đóng, hoặc
   thuê Runpod ~$0.4/h theo `training/serve/runpod_vllm.md`).
2. Chạy vLLM với bản AWQ (Runpod/VPS/GPU khác):
   ```bash
   vllm serve humanizer-vi --served-model-name humanizer-vi --api-key KEY_BẬT_MẬT --port 8000
   ```
3. Bật cho web app — sửa `web/backend/.env`:
   ```
   HUMANIZER_API_BASE=https://<host-vllm>:8000/v1
   HUMANIZER_API_KEY=KEY_BẬT_MẬT
   HUMANIZER_FALLBACK_GROQ=true     # giữ Groq làm dự phòng
   ```
   → `POST /api/humanize` tự chuyển sang model riêng của bạn; Groq chỉ dự phòng.
   `python training/doctor.py` phải báo `provider dự kiến: humanizer-model`.

## Dataset v1 — thông tin chốt (manifest `training/data/sft/manifest.json`)

| Chỉ số | Giá trị |
|---|---|
| Tổng cặp | **7.298** (6.573 train / 725 val) — split theo tài liệu, không rò rỉ |
| Register | literature 38% · blog (Wikivoyage) 18% · news (VNTC) 16% · wiki 15% · academic (Wikibooks) 12% |
| Generator | rule 7.235 · llm L2 63 (teacher Groq — quota free tier siết, tích thêm bằng cache) |
| QC cơ khí | 7.298/7.298 pass (fact-token, length ratio, reuse gate) |
| Provenance | `sources.jsonl` từng nguồn; riêng `raw/own/` ghi rõ "chỉ dùng nội bộ" (bài văn mẫu VietJack) |

## Lộ trình nâng cấp sau v1.3 (không bắt buộc hôm nay)

1. **Teacher enrichment tiếp tục**: chạy lại `prepare_dataset.py --dirtying llm` mỗi ngày
   quota Groq rảnh — cache tích lũy vĩnh viễn, rồi `build_mixed_from_cache.py` → v1.1
   với tỷ lệ L2/L3 cao hơn (văn AI "thật" hơn rule).
2. **DPO 2 vòng** theo blueprint humanize-zh: rejected pool từ output của chính model
   SFT + casual pool (UIT-VSFC/ViSFD).
3. **Judge bằng LLM khác** (Gemini free tier) khi cần audit độc lập thứ ba.
