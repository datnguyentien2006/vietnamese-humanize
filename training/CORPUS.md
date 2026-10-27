# Nguồn corpus văn người viết — tiêu chí, license, cách lấy

Mục tiêu P1: **5.000–20.000 cặp** `(văn AI, bản người viết cùng nội dung)`. Vì
chunking + lọc loại khoảng một nửa, cần **~2–4 triệu từ văn người** thô.

Nguyên tắc bất biến: **gold phải là người viết thật**. Không bao giờ lấy output
của model (kể cả model của bạn) làm gold — model sẽ học lại chính "tell" của nó
và chất lượng đi xuống sau mỗi vòng (model collapse).

## Nguồn nên dùng

| Nguồn | License | Ưu điểm | Cảnh báo | Tỉ lệ gợi ý |
|---|---|---|---|---|
| **Văn bản của chính bạn** (blog, báo cáo, luận văn, email dài) | của bạn | Đúng register, đúng giọng, sạch tuyệt đối | Ít về số lượng | 20–30% |
| **Wikisource tiếng Việt** (`vi.wikisource.org`) | Public domain hoặc CC BY-SA 4.0 | Văn xuôi Việt trước 1954, câu tự nhiên, nhiều | Chính tả cũ; lẫn thơ/kịch/văn bản hành chính — phải lọc | 30–40% |
| **Báo chí / tạp chí có license mở** | tuỳ nguồn | Đúng register news/report | Phải xin phép hoặc kiểm tra điều khoản từng nguồn | 20–30% |
| **Wikipedia tiếng Việt (dump)** | CC BY-SA 4.0 | Rất lớn, dễ lấy | Văn phong bách khoa, danh hóa nặng, câu đều — **dạy sai giọng nếu dùng nhiều** | ≤15% |
| **Bộ corpus nghiên cứu tiếng Việt** | tuỳ bộ | Đã chia sẵn | Tự đọc điều khoản; nhiều bộ là bản dịch máy | ≤15% |

Ghi nguồn + license cho từng tài liệu vào `training/data/raw/sources.jsonl`
(`fetch_corpus.py` làm việc này tự động). Không có provenance thì sau này không
dám dùng lại dataset.

## Không dùng

- Sách/báo còn bản quyền hiệu lực, nội dung tải lậu, file torrent.
- Văn bản **nghi do AI sinh** (sau 2022, không rõ nguồn) — đây là nhiễm độc
  nghiêm trọng nhất, ngược hoàn toàn mục tiêu.
- Bản dịch máy không biên tập: dạy model đúng cái "translationese" mà skill
  `translationese-cleaner-vi` đang cố xoá.
- Văn bản đã qua pipeline humanize của chính bạn (vòng lặp tự thưởng).

## Cách lấy

### Cách 1 — tự động (Wikisource, PD/CC)

```bash
python training/fetch_corpus.py --max-pages 800 --out training/data/raw
```

Mặc định lấy theo **thể loại văn xuôi** (`Truyện ngắn Việt Nam`, `Tiểu thuyết
Việt Nam`, `Truyện ngắn`, `Truyện Việt Nam`, `Truyện cười Việt Nam`), có mở một
cấp thể loại con. Script tự:

- loại **văn bản luật/hành chính** (theo tiêu đề và theo mật độ `Điều N.`) —
  đúng register mà dự án không được humanize máy móc;
- xoá dòng `Thể loại:...` lẫn trong trang và chuẩn hoá kiểu cũ "space trước dấu
  câu" (`nay ,` → `nay,`);
- lọc theo độ dài, số câu, tỉ lệ chữ có dấu, và loại đoạn thơ/vụn;
- ghi mỗi trang một `.txt` + provenance trong `sources.jsonl`, có `state.json`
  để chạy tiếp mà không tải lại.

Chạy lại nhiều lần để tăng dần. `--strategy random` để lấy ngẫu nhiên (nhanh
hơn nhưng phần lớn là văn bản luật — chỉ dùng khi cần thử).

### Cách 2 — thủ công (khuyến nghị cho văn của chính bạn)

Đặt file vào `training/data/raw/`, một trong các dạng:

- `.txt` / `.md`: toàn bộ file là một tài liệu (một bài, một chương).
- `.jsonl`: mỗi dòng `{"text": "..."}`; thêm `{"source": "...", "license": "..."}`
  nếu muốn giữ provenance.
- `.txt.gz`, `.parquet` (cột `text`).

Một file = **một tài liệu**; đừng gộp nhiều bài khác register vào một file, vì
split train/val được chia theo tài liệu.

### Cách 3 — dump Wikipedia (chỉ khi cần bổ sung)

Tải `viwiki-latest-pages-articles.xml.bz2`, trích văn bản bằng
`wikiextractor`, rồi đặt `.txt` vào `raw/`. Giữ tỉ lệ ≤15% và **không** trộn
vào tập validation.

## Kiểm tra trước khi train

```bash
python training/prepare_dataset.py --mode synthesize --source training/data/raw
cat training/data/sft/manifest.json
```

Đọc `manifest.json`: nếu `rejection_reasons.gold_noisy` cao bất thường, corpus
của bạn đang lẫn văn AI/dịch máy (bộ lọc chỉ tính finding `error` — lỗi chắc
chắn — nên heuristic về độ dài câu hay Hán-Việt không làm loại văn học thật).
Nếu `not_ai_flavoured` cao, dirtying chưa đủ mạnh. Nếu `fact_drift` > 0, **dừng
lại** — có lỗi logic, không được train.
