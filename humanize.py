"""
humanize.py — Bộ não humanize văn bản tiếng Việt.

Sử dụng skill humanizer-vi (SKILL.md) làm system prompt, gọi Gemini API
theo workflow: Lint → Read → Voice → Patterns → Rewrite → Audit → Output.

Cách dùng:
    python humanize.py <input.txt> <output.txt> [--lint <report.json>] [--voice <sample.txt>]
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("LỖI: Chưa cài google-genai. Chạy: pip install google-genai")
    sys.exit(1)


# ============================================================
#  CẤU HÌNH
# ============================================================
MODEL_NAME = "gemini-2.5-flash"
SKILL_PATH = Path(__file__).parent / "skills" / "humanizer-vi" / "SKILL.md"

# 30 dấu hiệu văn AI (dựa trên Signs of AI Writing của Wikipedia)
ANTI_AI_RULES = """
## 30 DẤU HIỆU VĂN AI CẦN LOẠI BỎ

### A. Dàn dựng thay vì nói thẳng
1. "Không phải X mà là Y" — nêu trực tiếp điểm chính.
2. Câu kết một dòng lặp lại ý — cắt bỏ.
3. Câu nghe có vẻ sâu sắc ("câu hỏi thật sự là", "cốt lõi là", "điều thật sự quan trọng là") — thay bằng tuyên bố cụ thể.
4. Mở đầu dàn dựng ("hãy cùng tìm hiểu", "đây là điều bạn cần biết", "giờ hãy xem xét") — bỏ, vào thẳng ý.
5. Tranh luận với người không tồn tại ("Điều này không nói về...", "Tôi không nói rằng...") — bỏ phần phòng vệ.

### B. Nhịp điệu theo quy tắc
6. Bộ ba gượng ép (3 ví dụ/ý song song) — gộp hoặc đa dạng hóa cấu trúc.
7. Mở đầu câu lặp lại (nhiều câu cùng bắt đầu bằng "Điều này", "Việc", "Chúng tôi") — đổi chủ ngữ hoặc gộp câu.
8. Dấu gạch ngang dài (—) làm dấu nối vạn năng — thay bằng dấu phẩy, dấu chấm, hoặc ngoặc đơn.
9. Chất đống từ hạn định ("có khả năng", "có thể được lập luận rằng") — giữ tối đa một.

### C. Thổi phồng và mượn uy tín
10. Từ Hán-Việt sáo rỗng — thay bằng từ thuần Việt:
    - đi sâu vào → tìm hiểu, phân tích
    - tận dụng → dùng, khai thác
    - bức tranh toàn cảnh → tổng quan
    - đóng vai trò quan trọng → quan trọng
    - mang tính cách mạng → mới, đột phá (khi thật sự đột phá)
    - thay đổi cuộc chơi → thay đổi cách làm
    - tối ưu hóa → cải thiện, làm tốt hơn
    - nâng cao nhận thức → giúp hiểu rõ hơn
    - khai thác tiềm năng → phát huy
    - điểm mấu chốt → điểm chính
    - yếu tố then chốt → yếu tố chính
    - giải pháp toàn diện → giải pháp đầy đủ
    - hệ sinh thái → hệ thống, môi trường
    - trải nghiệm người dùng → cách người dùng dùng
    - nâng tầm → cải thiện
    - kiến tạo → tạo, xây dựng
11. Bị động dày đặc ("được... bởi") — chuyển sang chủ động khi có thể.
12. Từ ngữ AI dùng quá nhiều ("thực sự", "thêm vào đó", "củng cố", "nâng cao", "thu hút", "làm nổi bật", "phức tạp", "then chốt", "tỉ mỉ", "mạnh mẽ", "đáng chú ý", "đa dạng", "phong phú", "sâu sắc") — thay thế hoặc bỏ.
13. Tầm quan trọng thổi phồng ("đánh dấu một khoảnh khắc then chốt", "đặt nền móng cho", "di sản lâu dài") — giữ sự kiện, bỏ tầm quan trọng.
14. Kết nối mơ hồ ("liên quan đến", "kết nối với", "trong mối liên hệ với") — nêu rõ mối quan hệ.
15. Đuôi "nhằm/để/qua đó" hời hợt — giữ sự kiện, chỉ giữ đuôi khi nguồn hỗ trợ.
16. Ngôn ngữ bán hàng ("nép mình", "ngoạn mục", "tuyệt đẹp", "không thể bỏ qua") — nêu sự vật là gì.
17. Mượn uy tín ("các chuyên gia lập luận", "các nhà quan sát đã trích dẫn") — cắt tuyên bố không được hỗ trợ.
18. Tránh "là" và "có" ("đóng vai trò như", "chức năng như") — dùng "là", "có".

### D. Định dạng theo quy tắc
19. In đậm như trang trí — bỏ in đậm không cần thiết.
20. Tiêu đề trang trí (viết hoa mọi từ, emoji, mũi tên) — dùng kiểu câu, bỏ trang trí.
21. Dấu ngoặc kép cong ("...") — thay bằng ngoặc kép thẳng ("...").

### E. Tàn dư từ chat
22. Tàn dư chatbot ("Tôi hy vọng điều này hữu ích", "Câu hỏi hay!", "Dưới đây là...", "Cho tôi biết nếu...") — bỏ.
23. Tuyên bố giới hạn kiến thức ("tính đến [ngày]", "trong khi chi tiết còn hạn chế") — nêu điều nguồn không cho thấy hoặc bỏ.
24. Tiêu đề lặp lại trong câu đầu — bỏ câu lặp.
25. Viết về tài liệu thay vì chủ đề ("được thêm vào để thay thế") — nêu chức năng thực tế.

### F. Viết cho sai độc giả
26. Giải thích lại điều độc giả đã biết — dẫn bằng quyết định, bỏ lý luận thừa.
27. Trạng từ hóa "một cách" và "mang tính" ("một cách hiệu quả", "mang tính đột phá") — bỏ "một cách"/"mang tính", giữ tính từ.

### G. Đặc thù tiếng Việt
28. Dịch sát từ tiếng Anh ("điều này cho phép chúng ta có thể", "có một số lý do tại sao", "khi nói đến", "về mặt của", "trong bối cảnh của", "nó là quan trọng để lưu ý rằng", "dựa trên thực tế rằng", "mặc dù thực tế là") — rút gọn.
29. Lạm dụng "các" và "những" — lược bỏ khi ngữ cảnh đã rõ.
30. Lạm dụng "đã", "đang", "sẽ" — lược bỏ khi ngữ cảnh thời gian đã rõ.

## QUY TẮC BẤT BIẾN (KHÔNG ĐƯỢC VI PHẠM)
1. KHÔNG thêm thông tin mới: không bịa số liệu, ví dụ, dẫn chứng, tên riêng, ngày tháng.
2. KHÔNG xóa thông tin gốc: mọi sự kiện, khái niệm, lập luận phải được giữ.
3. Giữ nguyên cấu trúc phân cấp: chương, mục, tiêu đề.
4. Giữ nguyên chú thích [^1], [1] và tài liệu tham khảo.
5. Không đổi tên riêng, đơn vị, viết tắt.
6. Không đổi ý nghĩa: "có thể" không thành "chắc chắn", "một số" không thành "tất cả".

## YÊU CẦU ĐẦU RA
- Trả lại CHỈ văn bản đã sửa, không giải thích, không thêm lời dẫn.
- Đa dạng độ dài câu: xen kẽ câu ngắn (5-10 từ) và câu dài (20-30 từ).
- Thêm đại từ nhân xưng phù hợp nếu văn bản quá khách quan (nhưng không lạm dụng).
"""


# ============================================================
#  HÀM TIỆN ÍCH
# ============================================================
def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("=" * 60)
        print("LỖI: Chưa cấu hình GEMINI_API_KEY")
        print("=" * 60)
        print("Lấy API key miễn phí tại: https://aistudio.google.com/apikey")
        print('Sau đó chạy: setx GEMINI_API_KEY "KEY_CUA_BAN"')
        print("Rồi mở lại Command Prompt.")
        sys.exit(1)
    return key


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"LỖI đọc file {path}: {e}")
        sys.exit(1)


def write_text(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def build_system_prompt():
    """Đọc skill humanizer-vi + thêm 30 dấu hiệu AI."""
    if not SKILL_PATH.exists():
        print(f"LỖI: Không tìm thấy skill tại {SKILL_PATH}")
        sys.exit(1)
    skill_content = read_text(SKILL_PATH)
    return skill_content + "\n\n" + ANTI_AI_RULES


def build_user_prompt(original, lint_report=None, voice_sample=None):
    """Xây dựng user prompt với văn bản gốc + lint report + voice sample."""
    parts = []

    if voice_sample:
        parts.append("## VĂN BẢN MẪU PHONG CÁCH CỦA NGƯỜI DÙNG\n")
        parts.append(voice_sample.strip())
        parts.append(
            "\n\nPhân tích phong cách của văn bản mẫu trên "
            "(độ dài câu, lựa chọn từ, dấu câu, cách mở đầu, chuyển ý) "
            "và áp dụng cho bản viết lại.\n"
        )

    if lint_report:
        parts.append("## LINT REPORT (các lỗi cần sửa)\n")
        parts.append(lint_report.strip())
        parts.append(
            "\n\nXử lý TẤT CẢ issue trong lint report TRƯỚC, "
            "sau đó rà lại 30 dấu hiệu AI trong system prompt.\n"
        )

    parts.append("## VĂN BẢN GỐC\n")
    parts.append(original.strip())

    parts.append(
        "\n\n---\n\nBây giờ thực hiện:\n"
        "1. Sửa tất cả issue trong lint report (nếu có).\n"
        "2. Rà lại toàn bộ 30 dấu hiệu văn AI trong system prompt và loại bỏ chúng.\n"
        "3. Đa dạng hóa độ dài câu (xen kẽ ngắn/dài).\n"
        "4. Giữ nguyên dữ kiện, số liệu, tên riêng, thuật ngữ.\n\n"
        "Xuất DUY NHẤT văn bản đã humanize "
        "(không giải thích, không tiêu đề phụ, không bảng so sánh)."
    )

    return "\n".join(parts)


def rewrite_pass(client, original, lint_report=None, voice_sample=None):
    """PASS 1: Viết lại theo skill + anti-AI rules."""
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(original, lint_report, voice_sample)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.5,
        ),
    )
    return response.text.strip()


def audit_pass(client, original, draft):
    """PASS 2: Audit lại bản nháp, sửa những gì còn sót."""
    system_prompt = build_system_prompt()
    audit_prompt = f"""Đây là bản nháp đã humanize từ một văn bản gốc.

## VĂN BẢN GỐC
{original.strip()}

## BẢN NHÁP ĐÃ HUMANIZE
{draft}

---

Bây giờ thực hiện AUDIT PASS:

1. Kiểm tra xem bản nháp có chứa thông tin/số liệu/ví dụ/tên riêng nào MỚI so với bản gốc không. Nếu có, xóa.
2. Kiểm tra xem có ý nào trong bản gốc bị mất trong bản nháp không. Nếu có, khôi phục.
3. Kiểm tra xem các chú thích [^1], [1], tài liệu tham khảo có còn nguyên vẹn không.
4. Quét lại 30 dấu hiệu AI trong system prompt, đặc biệt:
   - Dấu gạch ngang dài (—)
   - Bộ ba gượng ép
   - "Không chỉ... mà còn"
   - "Đóng vai trò quan trọng"
   - Từ nối dày ("đồng thời", "qua đó", "từ đó")
   - Câu đều nhịp (5+ câu có độ dài gần nhau)
   - Lạm dụng "các"/"những"/"đã"/"đang"/"sẽ"
5. Kiểm tra cấu trúc chương/mục/tiêu đề có bị đổi không.
6. Đọc thành tiếng xem nhịp điệu có tự nhiên không.

Sau khi audit, xuất DUY NHẤT phiên bản cuối cùng đã sửa.
Không giải thích. Không liệt kê lỗi đã sửa. Chỉ văn bản.
"""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=audit_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
        ),
    )
    return response.text.strip()


# ============================================================
#  MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Humanize văn bản tiếng Việt bằng Gemini + skill humanizer-vi."
    )
    parser.add_argument("input", help="File văn bản gốc (.txt)")
    parser.add_argument("output", help="File đầu ra (.txt)")
    parser.add_argument("--lint", help="File lint report (.json)", default=None)
    parser.add_argument(
        "--voice", help="File văn bản mẫu để hiệu chỉnh giọng (tùy chọn)", default=None
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Bỏ qua bước audit (nhanh hơn, chất lượng thấp hơn)",
    )
    args = parser.parse_args()

    # Đọc dữ liệu
    api_key = get_api_key()
    original = read_text(args.input)
    lint_report = (
        read_text(args.lint) if args.lint and os.path.exists(args.lint) else None
    )
    voice_sample = (
        read_text(args.voice) if args.voice and os.path.exists(args.voice) else None
    )

    print(f"  → Văn bản gốc: {len(original)} ký tự")
    print(f"  → Lint report: {'có' if lint_report else 'không'}")
    print(f"  → Voice sample: {'có' if voice_sample else 'không'}")
    print(f"  → Model: {MODEL_NAME}")
    print()

    # Khởi tạo client
    client = genai.Client(api_key=api_key)

    # PASS 1: Rewrite
    print("[PASS 1/2] Đang viết lại theo skill humanizer-vi + anti-AI rules...")
    try:
        draft = rewrite_pass(client, original, lint_report, voice_sample)
    except Exception as e:
        print(f"LỖI PASS 1: {e}")
        sys.exit(1)
    print(f"  → Bản nháp: {len(draft)} ký tự")

    # PASS 2: Audit
    if args.no_audit:
        final = draft
        print("[PASS 2/2] Bỏ qua audit (--no-audit)")
    else:
        print("[PASS 2/2] Đang audit và tinh chỉnh lần cuối...")
        try:
            final = audit_pass(client, original, draft)
        except Exception as e:
            print(f"CẢNH BÁO: PASS 2 thất bại ({e}). Dùng bản nháp của PASS 1.")
            final = draft
        print(f"  → Bản cuối: {len(final)} ký tự")

    # Ghi file
    write_text(args.output, final)
    print()
    print(f"THÀNH CÔNG: Đã lưu tại {args.output}")


if __name__ == "__main__":
    main()