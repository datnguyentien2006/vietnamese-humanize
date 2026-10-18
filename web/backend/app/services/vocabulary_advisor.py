"""Từ điển từ phổ thông tiếng Việt.

Module này cung cấp mapping từ Hán-Việt trang trọng (thường là dấu hiệu
văn AI hoặc dịch máy) sang từ phổ thông, tự nhiên hơn trong tiếng Việt
hàng ngày. Dùng để gợi ý cho user thay thế từ ngữ trong quá trình
"giảm đạo văn AI".

Nguồn tham khảo:
- Từ điển tiếng Việt thông dụng (Hoàng Phê chủ biên)
- Danh sách từ vựng phổ thông của Bộ Giáo dục và Đào tạo
- Các pattern hiện có trong dự án
"""

from __future__ import annotations

# Mapping: từ/cụm Hán-Việt trang trọng → gợi ý thay thế phổ thông
# Format: "cụm gốc": ["gợi ý 1", "gợi ý 2", ...]
FORMAL_TO_CASUAL: dict[str, list[str]] = {
    # === Động từ ===
    "tận dụng": ["dùng", "sử dụng", "khai thác"],
    "tối ưu hóa": ["cải thiện", "làm tốt hơn", "sắp xếp lại"],
    "tối đa hóa": ["tăng tối đa", "làm cho nhiều nhất có thể"],
    "nâng cao": ["cải thiện", "làm tốt hơn", "tăng"],
    "nâng tầm": ["làm cho tốt hơn", "phát triển"],
    "đẩy mạnh": ["tăng cường", "thúc đẩy", "làm mạnh hơn"],
    "thúc đẩy": ["khuyến khích", "tạo điều kiện"],
    "triển khai": ["thực hiện", "làm", "bắt đầu"],
    "thực hiện": ["làm", "tiến hành"],
    "tiến hành": ["làm", "bắt đầu"],
    "duy trì": ["giữ", "giữ cho"],
    "đảm bảo": ["chắc chắn", "làm cho chắc"],
    "đáp ứng": ["phù hợp với", "thỏa mãn"],
    "đối mặt": ["gặp phải", "chạm trán"],
    "giải quyết": ["xử lý", "làm xong"],
    "khắc phục": ["sửa", "sửa chữa"],
    "phát triển": ["làm cho lớn hơn", "mở rộng"],
    "mở rộng": ["làm cho lớn hơn", "phát triển thêm"],
    "cải tiến": ["cải thiện", "làm tốt hơn"],
    "cải thiện": ["làm tốt hơn", "sửa cho tốt hơn"],
    "tăng cường": ["làm mạnh hơn", "thêm vào"],
    "giảm thiểu": ["giảm", "làm cho ít đi"],
    "loại bỏ": ["bỏ", "xóa"],
    "xác định": ["tìm ra", "chỉ ra"],
    "phân tích": ["xem xét", "chia nhỏ để hiểu"],
    "đánh giá": ["xem xét", "nhìn nhận"],
    "nhận định": ["cho rằng", "nói rằng"],
    "kết luận": ["kết lại", "tóm lại"],
    "ghi nhận": ["nhận thấy", "thấy"],
    "chứng minh": ["cho thấy", "chỉ ra"],
    "thể hiện": ["cho thấy", "bộc lộ"],
    "biểu đạt": ["nói", "trình bày"],
    "truyền đạt": ["nói", "chia sẻ"],
    "tương tác": ["giao tiếp", "làm việc cùng"],
    "kết nối": ["nối", "gắn với"],
    "tích hợp": ["gộp vào", "kết hợp"],
    "đồng bộ": ["làm cho khớp", "cập nhật cùng lúc"],
    "phân phối": ["chia", "gửi đi"],
    "tiếp cận": ["đến gần", "tìm đến"],
    "khai thác": ["dùng", "lấy ra"],
    "vận hành": ["chạy", "hoạt động"],
    "điều hành": ["quản lý", "chỉ đạo"],
    "kiểm soát": ["quản lý", "theo dõi"],
    "giám sát": ["theo dõi", "trông coi"],
    
    # === Cụm từ ===
    "đóng vai trò quan trọng": ["rất quan trọng", "cần thiết"],
    "đóng vai trò then chốt": ["rất quan trọng", "quan trọng nhất"],
    "đóng vai trò chủ đạo": ["là chính", "chiếm phần lớn"],
    "mang lại lợi ích": ["có lợi", "giúp ích"],
    "tạo ra giá trị": ["có giá trị", "hữu ích"],
    "góp phần vào việc": ["giúp", "tham gia vào"],
    "có khả năng": ["có thể"],
    "có thể nói rằng": ["có thể nói", "có lẽ"],
    "trong bối cảnh": ["khi", "lúc"],
    "trong thời gian qua": ["gần đây", "thời gian vừa rồi"],
    "trong tương lai": ["sắp tới", "sau này"],
    "trong quá trình": ["khi", "lúc"],
    "thông qua việc": ["bằng cách", "nhờ"],
    "nhằm mục đích": ["để", "nhằm"],
    "với mục tiêu": ["để", "nhằm"],
    "dựa trên": ["theo", "dựa vào"],
    "liên quan đến": ["về", "có liên quan tới"],
    "phù hợp với": ["hợp với", "thích hợp"],
    "tương ứng với": ["tương ứng", "khớp với"],
    "song song với": ["cùng lúc", "song song"],
    "đi kèm với": ["kèm theo", "cùng với"],
    "cùng với đó": ["và", "cùng lúc đó"],
    "bên cạnh đó": ["ngoài ra", "hơn nữa"],
    "mặt khác": ["ngược lại", "bên kia"],
    "do đó": ["vì vậy", "nên"],
    "vì thế": ["nên", "vì vậy"],
    "bởi vậy": ["nên", "vì vậy"],
    "kết quả là": ["nên", "dẫn đến"],
    "dẫn đến": ["khiến cho", "làm cho"],
    "mặc dù": ["dù", "tuy"],
    "tuy nhiên": ["nhưng", "thế nhưng"],
    "ngược lại": ["trái lại", "còn"],
    "hơn nữa": ["và", "thêm nữa"],
    "thêm vào đó": ["và", "ngoài ra"],
    "đặc biệt là": ["nhất là", "đặc biệt"],
    "cụ thể là": ["như là", "tức là"],
    "chẳng hạn như": ["ví dụ", "như"],
    "ví dụ như": ["ví dụ", "như"],
    "nói cách khác": ["hiểu cách khác", "tức là"],
    "tóm lại": ["kết lại", "nói ngắn gọn"],
    "nhìn chung": ["nói chung", "đại khái"],
    "tổng thể": ["toàn bộ", "nói chung"],
    
    # === Tính từ / trạng từ ===
    "đáng kể": ["nhiều", "lớn"],
    "đáng chú ý": ["đáng để ý", "quan trọng"],
    "quan trọng": ["cần thiết", "đáng lưu tâm"],
    "cần thiết": ["cần", "quan trọng"],
    "hiệu quả": ["tốt", "có kết quả"],
    "hiệu suất": ["tốc độ", "kết quả"],
    "hiệu quả cao": ["rất tốt", "kết quả tốt"],
    "phù hợp": ["hợp", "thích hợp"],
    "khả thi": ["có thể làm được", "làm được"],
    "bền vững": ["lâu dài", "ổn định"],
    "toàn diện": ["đầy đủ", "mọi mặt"],
    "triệt để": ["hoàn toàn", "đến cùng"],
    "mạnh mẽ": ["mạnh", "rõ rệt"],
    "sâu sắc": ["sâu", "kỹ"],
    "tỉ mỉ": ["kỹ", "chi tiết"],
    "chi tiết": ["cụ thể", "rõ ràng"],
    "rõ ràng": ["rõ", "dễ hiểu"],
    "minh bạch": ["rõ ràng", "công khai"],
    "chặt chẽ": ["kỹ", "cẩn thận"],
    "linh hoạt": ["dễ thay đổi", "uyển chuyển"],
    "đa dạng": ["nhiều loại", "phong phú"],
    "phong phú": ["nhiều", "đa dạng"],
    "tiềm năng": ["có thể phát triển", "có triển vọng"],
    "thách thức": ["khó khăn", "thử thách"],
    "cơ hội": ["dịp", "thời cơ"],
    "rủi ro": ["nguy cơ", "khả năng gặp vấn đề"],
    "tác động": ["ảnh hưởng", "làm thay đổi"],
    "ảnh hưởng": ["tác động", "làm thay đổi"],
    "hậu quả": ["kết quả xấu", "tác hại"],
    "nguyên nhân": ["lý do", "do"],
    "giải pháp": ["cách giải quyết", "cách xử lý"],
    "phương pháp": ["cách", "cách làm"],
    "phương án": ["cách", "lựa chọn"],
    "chiến lược": ["kế hoạch", "cách làm lâu dài"],
    "chiến thuật": ["cách làm", "mẹo"],
    "quy trình": ["các bước", "cách làm"],
    "quy định": ["luật", "điều lệ"],
    "chính sách": ["quy định", "cách quản lý"],
    "hệ thống": ["bộ máy", "mạng lưới"],
    "cơ sở hạ tầng": ["hạ tầng", "nền tảng"],
    "nguồn lực": ["nguồn", "sức lực"],
    "nhân lực": ["người", "nhân viên"],
    "vật lực": ["của cải", "tiền của"],
    "tài chính": ["tiền", "ngân sách"],
    "ngân sách": ["tiền", "quỹ"],
    "doanh thu": ["thu nhập", "tiền kiếm được"],
    "lợi nhuận": ["lãi", "tiền lời"],
    "chi phí": ["phí", "tiền phải trả"],
    "đầu tư": ["bỏ tiền vào", "đổ tiền"],
    "thị trường": ["chỗ bán", "nơi mua bán"],
    "khách hàng": ["người mua", "khách"],
    "người tiêu dùng": ["người mua", "khách"],
    "sản phẩm": ["hàng", "mặt hàng"],
    "dịch vụ": ["phục vụ", "công việc phục vụ"],
    "trải nghiệm": ["cảm nhận", "trải qua"],
    "trải nghiệm người dùng": ["cảm nhận của người dùng", "người dùng thấy thế nào"],
    "giao diện": ["màn hình", "bề mặt"],
    "tính năng": ["chức năng", "công dụng"],
    "chức năng": ["công dụng", "việc làm được"],
    "công nghệ": ["kỹ thuật", "máy móc"],
    "kỹ thuật": ["cách làm", "công nghệ"],
    "dữ liệu": ["số liệu", "thông tin"],
    "thông tin": ["tin", "dữ liệu"],
    "kiến thức": ["hiểu biết", "biết"],
    "kinh nghiệm": ["từng làm", "đã trải qua"],
    "năng lực": ["khả năng", "sức"],
    "kỹ năng": ["khả năng", "tay nghề"],
    "trình độ": ["mức", "khả năng"],
    "chuyên môn": ["nghề", "ngành"],
    "nghiệp vụ": ["công việc", "việc chuyên môn"],
    "đào tạo": ["dạy", "huấn luyện"],
    "hướng dẫn": ["chỉ", "dạy"],
    "tư vấn": ["góp ý", "khuyên"],
    "hỗ trợ": ["giúp", "giúp đỡ"],
    "phối hợp": ["làm cùng", "kết hợp"],
    "tham gia": ["góp mặt", "dự vào"],
    "đóng góp": ["góp", "cho vào"],
    "chia sẻ": ["nói ra", "kể"],
    "trao đổi": ["nói chuyện", "bàn"],
    "thảo luận": ["bàn", "nói chuyện"],
    "tranh luận": ["cãi", "bàn cãi"],
    "phản hồi": ["trả lời", "góp ý"],
    "thông báo": ["báo", "cho biết"],
    "báo cáo": ["trình bày", "kể lại"],
    "đề xuất": ["gợi ý", "đề nghị"],
    "kiến nghị": ["đề nghị", "xin"],
    "yêu cầu": ["xin", "đòi"],
    "đề nghị": ["xin", "mời"],
    "khuyến nghị": ["gợi ý", "khuyên"],
    "khuyến khích": ["động viên", "khích lệ"],
    "động viên": ["khích lệ", "an ủi"],
    "thuyết phục": ["làm cho tin", "nói cho nghe"],
    "thương lượng": ["trả giá", "bàn giá"],
    "đàm phán": ["bàn", "thương lượng"],
    "hợp tác": ["làm cùng", "bắt tay"],
    "liên kết": ["nối", "gắn"],
    "hợp nhất": ["gộp", "nhập lại"],
    "sáp nhập": ["gộp", "nhập vào"],
    "chia tách": ["tách ra", "chia"],
    "tái cấu trúc": ["sắp xếp lại", "tổ chức lại"],
    "chuyển đổi": ["đổi", "thay đổi"],
    "thay đổi": ["đổi", "biến đổi"],
    "biến đổi": ["thay đổi", "đổi khác"],
    "chuyển biến": ["thay đổi", "tiến triển"],
    "tiến triển": ["phát triển", "đi lên"],
    "phát triển": ["lớn lên", "mở rộng"],
    "tăng trưởng": ["tăng", "lớn lên"],
    "suy giảm": ["giảm", "yếu đi"],
    "suy thoái": ["đi xuống", "yếu đi"],
    "khủng hoảng": ["nguy cấp", "lúc khó khăn"],
    "biến động": ["thay đổi", "dao động"],
    "ổn định": ["yên", "không đổi"],
    "bất ổn": ["không yên", "hay thay đổi"],
}


def get_casual_suggestions(phrase: str, max_suggestions: int = 3) -> list[str]:
    """Trả về danh sách gợi ý từ phổ thông cho một cụm từ.

    Tìm kiếm chính xác trước, sau đó tìm kiếm không phân biệt hoa thường.
    Nếu không tìm thấy, trả về danh sách rỗng.
    """
    if not phrase:
        return []
    
    # Tìm chính xác
    if phrase in FORMAL_TO_CASUAL:
        return FORMAL_TO_CASUAL[phrase][:max_suggestions]
    
    # Tìm không phân biệt hoa thường
    phrase_lower = phrase.lower()
    for key, values in FORMAL_TO_CASUAL.items():
        if key.lower() == phrase_lower:
            return values[:max_suggestions]
    
    return []


def get_all_formal_phrases() -> dict[str, list[str]]:
    """Trả về toàn bộ mapping để frontend có thể hiển thị dictionary."""
    return dict(FORMAL_TO_CASUAL)