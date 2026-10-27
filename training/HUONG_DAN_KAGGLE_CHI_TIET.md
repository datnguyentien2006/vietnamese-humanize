# Hướng dẫn Kaggle từ A→Z — train vi-humanizer v1.3 (7B, T4 miễn phí)

> Dành cho người **chưa từng dùng Kaggle**. Làm đúng thứ tự, mỗi bước có lệnh copy-paste.
> Tổng thời gian thao tác của bạn: **~15 phút**. Train chạy trên cloud: **2–4 giờ**.
> Máy bạn có thể tắt trong lúc train — Kaggle chạy độc lập.

**Chuẩn bị:** file `training\data\upload_dataset_v2.zip` (18,3 MB — đã có sẵn),
tài khoản Google, **số điện thoại** (để xác minh Kaggle).

---

## BƯỚC 1 — Tạo tài khoản Kaggle + xác minh SĐT (bắt buộc, 5 phút)

1. Mở **https://www.kaggle.com** → bấm **Register** → chọn **Continue with Google**
   (hoặc đăng ký email).
2. Bấm **ảnh đại diện (góc phải trên)** → **Settings**.
3. Kéo xuống mục **Phone Verification** → nhập số điện thoại VN
   (định dạng `+84xxxxxxxxx`) → nhận mã SMS → nhập mã → **Verify**.
   > ⚠️ **Không xác minh SĐT = không bật được GPU và Internet** — bắt buộc.
4. Vẫn trong **Settings** → mục **API** → bấm **Create New Token**.
   → Trình duyệt tải về file **`kaggle.json`**.
5. Chép file đó vào đúng thư mục này (tạo thư mục nếu chưa có):

   ```powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.kaggle" | Out-Null
   Copy-Item "$env:USERPROFILE\Downloads\kaggle.json" "$env:USERPROFILE\.kaggle\kaggle.json" -Force
   Test-Path "$env:USERPROFILE\.kaggle\kaggle.json"    # phải in ra True
   ```

---

## BƯỚC 2 — Upload dataset (3 phút)

1. Trên Kaggle, menu trái → **Datasets** → nút **New Dataset**
   (hoặc nút **+ Create** góc trái trên → **Dataset**).
2. **Kéo thả** file `C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer\training\data\upload_dataset_v2.zip`
   vào khung upload. Chờ upload xong (18,3 MB, nhanh).
3. Điền:
   - **Title**: `vi-humanizer-corpus`
   - **URL/slug**: giữ mặc định `vi-humanizer-corpus`
   - **Visibility**: chọn **Private**
4. Bấm **Create** (góc phải). Chờ 1–2 phút Kaggle giải nén.
5. Kiểm tra: trang dataset hiện **~3.681 files** (3.679 file `.txt` + `train.jsonl`
   + `val.jsonl`). Nếu chỉ thấy 1 file zip → bấm **Create** lại từ bước 2, Kaggle
   đôi khi không tự giải nén khi upload bằng kéo thả.

> Ghi nhớ tên dataset: **`vi-humanizer-corpus`** — bước sau cần đúng tên này.

---

## BƯỚC 3 — Cài Kaggle CLI (1 phút)

Mở **PowerShell** (Windows Start → gõ "PowerShell" → Enter), dán nguyên khối:

```powershell
Set-Location 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer'
.\.venv\Scripts\python.exe -m pip install -q kaggle
.\.venv\Scripts\kaggle.exe whoami
```

- Nếu in ra **username** của bạn (không phải chữ "Error") → OK.
- Nếu lỗi `401`/`403`: `kaggle.json` sai chỗ → làm lại Bước 1.5.

---

## BƯỚC 4 — Sửa 2 dòng trong metadata (1 phút)

Mở file **`C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer\training\remote\kernel-metadata.json`**
bằng Notepad, sửa **đúng 2 chỗ** (giữ nguyên phần còn lại):

```json
{
  "id": "TEN_KAGGLE_CUA_BAN/humanizer-vi-train",
  "code_file": "humanizer_colab.ipynb",
  "language_type": "notebook",
  "id_is_slug": false,
  "is_private": true,
  "enable_gpu": true,
  "enable_tpu": false,
  "enable_internet": true,
  "dataset_sources": ["TEN_KAGGLE_CUA_BAN/vi-humanizer-corpus"],
  "kernel_sources": [],
  "competition_sources": [],
  "model_sources": []
}
```

- `TEN_KAGGLE_CUA_BAN` = username in ra ở `kaggle whoami` (vd: `nguyenvana`).
- Lưu file (Ctrl+S).

---

## BƯỚC 5 — Push (1 phút)

```powershell
Set-Location 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer\training\remote'
..\..\.venv\Scripts\kaggle.exe kernels push
```

Kết quả mong đợi:

```
Kernel push URL: https://www.kaggle.com/code/TEN_BAN/humanizer-vi-train
...
Kernel version 1 successfully pushed.
```

→ Mở link đó trong trình duyệt là xem được tiến trình trực tiếp (tab **Logs**).

**Trong 3–5 phút đầu**, log phải hiện lần lượt:
```
GPU: Tesla T4
setup ok
linked: /kaggle/input/vi-humanizer-corpus
prebuilt SFT copied: ['train.jsonl', 'val.jsonl']
PREBUILT SFT FOUND — dùng train/val đã upload, bỏ qua prepare_dataset
```
→ Nếu thấy đúng 4 dòng này = mọi thứ chuẩn, train đã bắt đầu.

---

## BƯỚC 6 — Theo dõi (không cần ngồi canh)

```powershell
Set-Location 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer'
.\.venv\Scripts\kaggle.exe kernels status TEN_KAGGLE_CUA_BAN/humanizer-vi-train
```

Các trạng thái: `queued` (xếp hàng) → `running` → `complete`.
Hoặc mở link Kaggle → tab **Logs** xem trực tiếp.

**Tiến trình dự kiến (7B, T4):**
| Giai đoạn | Thời gian |
|---|---|
| Setup + tải model 7B | 5–10 phút |
| **Train QLoRA 411 steps** | **2–4 giờ** |
| Merge + AWQ export | 20–40 phút |
| **Tổng** | **~3–5 giờ** |

> Kaggle tự dừng notebook sau **9 giờ/session** — với 7B bạn còn rất nhiều dư.

---

## BƯỚC 7 — Tải kết quả (khi status = complete)

```powershell
Set-Location 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer'
.\.venv\Scripts\kaggle.exe kernels output TEN_KAGGLE_CUA_BAN/humanizer-vi-train -p training\output\kaggle_run
```

Bạn sẽ có trong `training\output\kaggle_run\`:
- `humanizer-lora/` — adapter (~150 MB)
- `humanizer-awq/` — **model AWQ (~4,5 GB)** ← dùng cái này để serve
- `train.log` — log train đầy đủ

→ **Nhắn tôi "train xong rồi"** — tôi lo phần serve vLLM (hoặc Ollama GGUF) trên GPU 6 GB
của bạn + nối `HUMANIZER_API_BASE` để web app v1.3 dùng model riêng.

---

## Sự cố thường gặp & cách xử lý

| Lỗi / hiện tượng | Nguyên nhân & cách sửa |
|---|---|
| `403 Forbidden` khi push | Chưa **xác minh SĐT** hoặc `kaggle.json` sai chỗ → làm lại Bước 1 |
| `Dataset not found` | Slug sai: phải là `TEN_BAN/vi-humanizer-corpus` (chữ thường) |
| Bấm **New Dataset** không thấy mục GPU | Bình thường — GPU bật ở bước Notebook, không phải Dataset |
| Log không có "GPU: Tesla T4" | Notebook chưa bật GPU → Edit → Settings → Accelerator → **GPU T4 x2** |
| Log dừng ở bước pip install | Kaggle mất mạng tạm thời → Edit → **Run All** lại |
| `CUDA out of memory` | Notebook tự fallback 7B (đã mặc định 7B) → nếu vẫn lỗi: `LIMIT = 4000` trong cell CONFIG |
| `Your notebook was stopped` | Hết 9 giờ hoặc bị ngắt → mở link, bấm **Run All** lại (dữ liệu cloud giữ nguyên) |
| Chỉ thấy 1 file .zip trong dataset | Upload lại bằng nút kéo thả, hoặc giải nén zip rồi upload cả thư mục |
| `kaggle.exe` không tồn tại | Chạy lại `pip install kaggle` ở Bước 3 |

## Lưu ý về quota

- Kaggle cho **30 giờ GPU/tuần** (T4). Run này tốn ~4–5 giờ → dư sức train lại 2–3 lần
  khi teacher local hoàn thành v2.1.
- Dataset private, không public — an toàn cho dự án cá nhân.

## Sau khi có model — bước cuối (tôi làm cùng bạn)

1. `humanizer-awq/` (4,5 GB) → chạy vLLM trên máy bạn với cờ `--gpu-memory-utilization 0.92
   --max-model-len 2048` (vừa 6 GB VRAM) hoặc convert GGUF Q4 chạy Ollama (nhẹ hơn).
2. Đặt trong `web\backend\.env`: `HUMANIZER_API_BASE=http://127.0.0.1:8000/v1`
3. `python training\doctor.py` → phải báo `provider: humanizer-model`
4. Mở web app → dán văn AI → Humanize → **model của chính bạn trả lời**. 🎉
