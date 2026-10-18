"""Script debug: kiểm tra lint_text trả về gì."""
import json
from vietnamese_writing_skills.cli.lint import lint_text

TEST_TEXT = """Đoàn kết của sinh viên vào xây dựng và phát triển Trường Đại học Bách khoa – ĐHQG. HCM hiện nay rất quan trọng.

Phương pháp thảo luận nhóm hay nghiên cứu liên ngành hiện nay tạo nhiều cơ hội giao tiếp cho người học."""

print("=" * 60)
print("TEST 1: lint_text raw output")
print("=" * 60)
results = lint_text(TEST_TEXT)
print(json.dumps(results, ensure_ascii=False, indent=2))

print()
print("=" * 60)
print("TEST 2: Kiểm tra keys trong occurrence đầu tiên")
print("=" * 60)
if results:
    first = results[0]
    print("Item keys:", sorted(first.keys()))
    occ = first.get("occurrences", [])
    if occ:
        print("Occurrence[0] keys:", sorted(occ[0].keys()))
        print("Occurrence[0].start =", occ[0].get("start"))
        print("Occurrence[0].paragraph =", repr(occ[0].get("paragraph", ""))[:80])