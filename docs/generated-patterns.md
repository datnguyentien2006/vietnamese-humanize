# Danh mục pattern (được sinh tự động)

> Không sửa trực tiếp file này. Chạy `python scripts/generate_pattern_docs.py` sau khi đổi YAML.

## VI-GRA-C01: `cac-nhung-chong-nhau`

- Skill: `grammar-checker-vi`
- Finding type: `error`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Dùng đồng thời "các" và "những" trước cùng một danh từ mà không có chức năng riêng.
- Rewrite strategy:
  - Giữ "các" cho tập xác định hoặc "những" cho một số phần tử tùy ý nghĩa.
- Good examples:
  - `clean_rewrite`: Các tài liệu này cần được lưu lại.
  - `clean_rewrite`: Những nhân viên trên đều đã xử lý yêu cầu.
- Exceptions:
  - Nội dung trích dẫn nguyên văn hoặc đang phân tích chính lỗi này.

## VI-GRA-C02: `boi-vi-cho-nen`

- Skill: `grammar-checker-vi`
- Finding type: `preference`
- Scope / aggregation: `sentence` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `high`
- Tóm tắt: Kết hợp "bởi vì" và "cho nên" trong câu ngắn khi một vế nối đã đủ rõ.
- Rewrite strategy:
  - Giữ một đầu nối khi câu viết cần gọn; giữ cả hai nếu nhịp nói hoặc cấu trúc dài cần đánh dấu.
- Good examples:
  - `clean_rewrite`: Vì trời mưa, trận đấu bị hoãn.
  - `clean_rewrite`: Máy hết pin nên dữ liệu chưa đồng bộ.
- Exceptions:
  - Văn nói, lời thoại, câu dài cần đánh dấu rõ hai vế hoặc phong cách tác giả.

## VI-GRA-C03: `tham-chieu-dieu-nay-day-dac`

- Skill: `grammar-checker-vi`
- Finding type: `warning`
- Scope / aggregation: `paragraph` / `count`
- Severity / confidence: `medium` / `low`
- False-positive risk: `high`
- Tóm tắt: Lặp "điều này" nhiều lần khi phần được tham chiếu có thể không rõ.
- Rewrite strategy:
  - Gọi tên sự việc được tham chiếu khi có hơn một tiền tố hợp lý; nếu chưa rõ thì hỏi tác giả.
- Good examples:
  - `clean_rewrite`: Việc máy chủ dừng giữa lúc sao lưu làm nhóm lo ngại.
    - Context: Nhóm xác nhận việc máy chủ dừng là nguyên nhân gây lo ngại.
  - `clean_rewrite`: Tin Mai nghỉ việc khiến quản lý bất ngờ.
    - Context: Lan xác nhận Mai là người đã nghỉ.
- Exceptions:
  - Khi câu trước chỉ có một mệnh đề và tham chiếu không thể hiểu theo cách khác.

## VI-GRA-C04: `dau-phay-tach-chu-vi`

- Skill: `grammar-checker-vi`
- Finding type: `heuristic`
- Scope / aggregation: `sentence` / `single`
- Severity / confidence: `medium` / `low`
- False-positive risk: `high`
- Tóm tắt: Dấu phẩy có thể đang tách chủ ngữ khỏi vị ngữ mà không có thành phần chen giữa.
- Rewrite strategy:
  - Đọc cấu trúc câu; xóa dấu phẩy chỉ khi không có mệnh đề hoặc thành phần chen hợp lệ.
- Good examples:
  - `clean_rewrite`: Báo cáo mới của nhóm đã được gửi sáng nay.
  - `clean_rewrite`: Hệ thống theo dõi đơn hàng và sẽ gửi cảnh báo khi có lỗi.
- Exceptions:
  - Khi giữa chủ ngữ và vị ngữ có thành phần chen, chú thích hoặc mệnh đề phụ.

## VI-GRA-C05: `cap-tu-noi-khong-khop`

- Skill: `grammar-checker-vi`
- Finding type: `error`
- Scope / aggregation: `sentence` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Dùng "không những/không chỉ ... nhưng còn" thay vì cặp tương ứng "... mà còn".
- Rewrite strategy:
  - Đổi "nhưng còn" thành "mà còn", hoặc viết lại hai vế bằng một cấu trúc song song khác.
- Good examples:
  - `clean_rewrite`: Phương án không những tiết kiệm chi phí mà còn rút ngắn thời gian xử lý.
  - `clean_rewrite`: Công cụ nhanh và dễ sử dụng.
- Exceptions:
  - Trích dẫn nguyên văn hoặc nội dung đang phân tích chính cấu trúc này.

## VI-GRA-C06: `vi-vay-nen`

- Skill: `grammar-checker-vi`
- Finding type: `preference`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `low` / `high`
- False-positive risk: `medium`
- Tóm tắt: Dùng đồng thời "vì vậy" và "nên" khi một từ nối đã đủ thể hiện quan hệ kết quả.
- Rewrite strategy:
  - Giữ "vì vậy" hoặc "nên" khi cả hai cùng chỉ kết quả. Nếu "nên" đang khuyên một hành động, giữ nguyên.
- Good examples:
  - `clean_rewrite`: Vì vậy, công ty sẽ áp dụng phương án mới.
  - `clean_rewrite`: Máy hết pin nên dữ liệu chưa được đồng bộ.
  - `no_change`: Vì vậy, nên sao lưu dữ liệu trước khi nâng cấp.
    - Reason: "nên" ở đây là lời khuyên, không phải từ nối kết quả thừa.
  - `no_change`: Vì vậy, nên chọn người có kinh nghiệm.
    - Reason: "nên" khuyên một hành động; "có" trong "có kinh nghiệm" không phải trợ từ kết quả.
  - `no_change`: Vì vậy, nên nghỉ. Tôi sẽ quay lại.
    - Reason: Không đọc trợ từ ở câu sau để kết luận "nên" thừa.
  - `no_change`: Vì vậy, nên chọn người đã làm việc ở đây.
    - Reason: "đã" nằm trong mệnh đề bổ nghĩa, không biến "nên" thành liên từ kết quả thừa.
  - `no_change`: Vì vậy, nên chọn máy được bảo hành.
    - Reason: "được" trong "được bảo hành" không đủ để kết luận "nên" thừa.
  - `no_change`: Vì vậy, nên mua máy đang giảm giá.
    - Reason: Không đủ chắc "nên" là liên từ kết quả chỉ vì động từ không nằm trong danh sách có sẵn.
  - `no_change`: Vì vậy, nên thuê người đã có kinh nghiệm.
    - Reason: "nên thuê" là lời khuyên; "đã" nằm trong mệnh đề bổ nghĩa.
  - `no_change`: Vì vậy, nên ưu tiên máy được bảo hành.
    - Reason: Giữ nguyên khi không tách được vai trò khuyến nghị và liên từ kết quả.
  - `no_change`: Vì vậy, nên công bố bản đã duyệt.
    - Reason: "công bố" là động từ; không suy chủ ngữ từ âm tiết "công".
  - `no_change`: Vì vậy, nên công nhận người đã đóng góp.
    - Reason: "công nhận" là động từ khuyến nghị, không phải chủ ngữ "công ty".
  - `no_change`: Vì vậy, nên dự thi khi đã chuẩn bị kỹ.
    - Reason: "dự thi" là động từ; không suy chủ ngữ từ âm tiết "dự".
- Exceptions:
  - Khi "nên" mang nghĩa khuyến nghị; lời thoại cần giữ nguyên khẩu ngữ hoặc trích dẫn nguyên văn. Nếu không tách được hai vai trò, giữ nguyên.

## VI-GRA-L01: `lap-tu-lien-tiep`

- Skill: `grammar-checker-vi`
- Finding type: `error`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Một từ bị lặp ngay cạnh nhau do lỗi gõ hoặc sửa câu chưa hết.
- Rewrite strategy:
  - Xóa một lần lặp sau khi chắc hai từ không thuộc cấu trúc nhấn mạnh có chủ đích.
- Good examples:
  - `clean_rewrite`: Nhóm sẽ gửi kết quả vào chiều nay.
  - `clean_rewrite`: Hệ thống đang khởi động lại.
  - `no_change`: Người người, nhà nhà đều hướng về quê.
    - Reason: Phép lặp có nghĩa, không phải lỗi gõ.
  - `no_change`: Bạn cứ từ từ đọc báo cáo.
    - Reason: Từ láy "từ từ" nằm trong exclude_phrases.
- Exceptions:
  - Phép lặp biểu cảm, từ láy, lời thoại, thơ hoặc ví dụ đang phân tích chính từ đó.

## VI-GRA-L02: `chuan-doan-sai-chinh-ta`

- Skill: `grammar-checker-vi`
- Finding type: `error`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `high` / `high`
- False-positive risk: `low`
- Tóm tắt: Viết "chuẩn đoán" khi nghĩa cần dùng là hoạt động chẩn đoán bệnh hoặc lỗi.
- Rewrite strategy:
  - Đổi thành "chẩn đoán" khi nói đến việc xác định bệnh, tình trạng hoặc nguyên nhân lỗi.
- Good examples:
  - `clean_rewrite`: Bác sĩ chẩn đoán bệnh nhân bị viêm phổi.
  - `clean_rewrite`: Công cụ hỗ trợ chẩn đoán lỗi mạng.
- Exceptions:
  - Trích dẫn nguyên văn, tên riêng hoặc nội dung đang minh họa lỗi chính tả.

## VI-GRA-L03: `sat-nhap-sai-chinh-ta`

- Skill: `grammar-checker-vi`
- Finding type: `error`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Viết "sát nhập" khi nghĩa phổ thông cần dùng là "sáp nhập".
- Rewrite strategy:
  - Đổi thành "sáp nhập" nếu không phải tên riêng hoặc trích dẫn.
- Good examples:
  - `clean_rewrite`: Hai phòng ban sẽ sáp nhập từ tháng 8.
  - `clean_rewrite`: Kế hoạch sáp nhập đã được công bố.
- Exceptions:
  - Tên tác phẩm, trích dẫn hoặc dữ liệu cần giữ nguyên chính tả nguồn.

## VI-GRA-P01: `khoang-trang-truoc-dau-cau`

- Skill: `grammar-checker-vi`
- Finding type: `error`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Có khoảng trắng thừa trước dấu chấm, phẩy, hỏi, than, hai chấm hoặc chấm phẩy.
- Rewrite strategy:
  - Xóa khoảng trắng trước dấu câu, trừ khi nội dung thuộc code hoặc dữ liệu đặc thù.
- Good examples:
  - `clean_rewrite`: Báo cáo đã xong, vui lòng kiểm tra.
  - `clean_rewrite`: Bạn đã nhận được email chưa?
- Exceptions:
  - Code, biểu thức, dữ liệu nguyên bản hoặc style typography chuyên biệt.

## VI-GRA-P02: `thieu-khoang-trang-sau-dau-cau`

- Skill: `grammar-checker-vi`
- Finding type: `error`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `medium`
- Tóm tắt: Thiếu khoảng trắng sau dấu câu khi một từ mới bắt đầu trên cùng dòng.
- Rewrite strategy:
  - Thêm một khoảng trắng sau dấu câu nếu đây không phải số, URL, code hay viết tắt.
- Good examples:
  - `clean_rewrite`: Bản A đã duyệt, bản B còn chờ.
  - `clean_rewrite`: Lưu ý: không tắt máy.
  - `no_change`: Gửi hotro@example.com hoặc xem README.md tại TP.HCM.
    - Reason: Email, tên tệp và viết tắt giữ dấu chấm sát chữ.
- Exceptions:
  - Số thập phân, URL, email, phiên bản, code, identifier, tên tệp và viết tắt như TP.HCM.

## VI-GRA-P03: `dau-cau-lap`

- Skill: `grammar-checker-vi`
- Finding type: `preference`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `low` / `medium`
- False-positive risk: `high`
- Tóm tắt: Lặp nhiều dấu hỏi hoặc dấu than trong văn bản không cần nhấn mạnh cảm xúc.
- Rewrite strategy:
  - Giữ một dấu; nếu cảm xúc có chủ đích trong mạng xã hội thì để nguyên.
- Good examples:
  - `clean_rewrite`: Vui lòng gửi báo cáo ngay!
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Vì sao hệ thống dừng?
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Hội thoại, mạng xã hội, trích dẫn và văn chương dùng dấu lặp có chủ đích.

## VI-GRA-P04: `ngoac-khong-can`

- Skill: `grammar-checker-vi`
- Finding type: `preference`
- Scope / aggregation: `document` / `single`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Ngoặc hoặc dấu nháy mở/đóng không cân; cần người viết kiểm tra, không tự đoán chỗ đóng.
- Rewrite strategy:
  - Đánh dấu để người viết kiểm tra. Không tự thêm dấu đóng hay đổi vị trí ngoặc.
- Good examples:
  - `no_change`: Báo cáo “quý 3” vẫn chưa đóng.
  - `no_change`: Xem [hướng dẫn](https://example.com/docs).
    - Reason: Link Markdown cân ngoặc; URL không được che mất dấu đóng.
  - `no_change`: Truy cập "https://example.com" để đọc thêm.
    - Reason: URL trong ngoặc kép không được nuốt dấu đóng.
  - `no_change`: Truy cập “https://example.com” để đọc thêm.
    - Reason: URL trong ngoặc kép cong không được nuốt dấu đóng.
  - `no_change`: Xem https://example.com/a(b) để biết thêm.
    - Reason: Ngoặc thuộc đường dẫn URL phải được che cùng nhau.
  - `no_change`: Kết nối http://[::1]:8000/ để thử.
    - Reason: Ngoặc vuông của IPv6 thuộc URL, không phải ngoặc thiếu cặp.
  - `no_change`: 1) Mở ứng dụng. 2) Chọn báo cáo.
    - Reason: Dấu đóng trong ký hiệu đánh số không phải ngoặc đơn cần cặp.
  - `review_comment`: Cần người viết kiểm tra ngoặc đơn, không tự thêm dấu đóng.
    - Reason: Không tự đoán vị trí đóng.
- Exceptions:
  - Code, biểu thức, emoji, và trích đoạn cố ý để mở.

## VI-GRA-S01: `bi-dong-va-chu-ngu-thieu`

- Skill: `grammar-checker-vi`
- Finding type: `heuristic`
- Scope / aggregation: `sentence` / `count`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `high`
- Tóm tắt: Câu bị động dày đặc hoặc thiếu chủ ngữ, che giấu người hành động.
- Rewrite strategy:
  - Chuyển sang thể chủ động khi có thể xác định được người hành động.
  - Thêm chủ ngữ nếu câu thiếu và ngữ cảnh cho phép.
- Good examples:
  - `clean_rewrite`: Bạn không cần tệp cấu hình. Hệ thống tự động giữ kết quả và xử lý dữ liệu.
    - Reason: Chuyển sang chủ động, thêm chủ ngữ.
  - `clean_rewrite`: Nhóm kỹ thuật hoàn thành báo cáo. Quản lý xác nhận kết quả.
    - Reason: Đưa chủ thể lên đầu, câu ngắn hơn.
- Exceptions:
  - Phương pháp khoa học ưu tiên đối tượng.
  - Tác nhân không quan trọng hoặc không xác định.

## VI-HUM-D01: `mo-bai-thong-bao-noi-dung`

- Skill: `humanizer-vi`
- Finding type: `preference`
- Scope / aggregation: `document` / `single`
- Severity / confidence: `low` / `high`
- False-positive risk: `low`
- Tóm tắt: Mở bài thông báo "trong bài viết này" thay vì đi thẳng vào chủ đề.
- Rewrite strategy:
  - Mở bằng vấn đề, kết luận chính hoặc bối cảnh cụ thể.
- Good examples:
  - `clean_rewrite`: Cache giữ dữ liệu đã đọc để giảm số lần truy cập nguồn.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Ba nguyên tắc này giúp API thay đổi mà không phá client cũ.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Trong syllabus, proposal hoặc tài liệu dài cần nêu rõ phạm vi và cấu trúc.

## VI-HUM-D02: `ket-bai-xa-giao`

- Skill: `humanizer-vi`
- Finding type: `preference`
- Scope / aggregation: `document` / `single`
- Severity / confidence: `low` / `high`
- False-positive risk: `low`
- Tóm tắt: Kết thúc bằng lời xã giao chung chung không bổ sung hành động hoặc thông tin.
- Rewrite strategy:
  - Kết ở thông tin cuối cùng hoặc nêu bước tiếp theo có thật.
- Good examples:
  - `clean_rewrite`: Cấu hình mới có hiệu lực từ lần khởi động tiếp theo.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Nhóm sẽ chốt phương án tại cuộc họp ngày 25 tháng 7.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Trong thư cá nhân hoặc trao đổi chăm sóc khách hàng khi lời chúc phù hợp quan hệ.

## VI-HUM-D03: `dan-nguon-mo-ho`

- Skill: `humanizer-vi`
- Finding type: `warning`
- Scope / aggregation: `sentence` / `single`
- Severity / confidence: `high` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Gán nhận định cho "các chuyên gia" hoặc "nhiều nghiên cứu" mà không xác định nguồn.
- Rewrite strategy:
  - Nêu nguồn có sẵn; nếu không có, thu hẹp tuyên bố hoặc đánh dấu cần nguồn.
- Good examples:
  - `review_comment`: Cần bổ sung nguồn cụ thể cho nhận định rằng phương pháp hoàn toàn an toàn.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `review_comment`: Cần xác định các nghiên cứu về tác động của mô hình lên năng suất.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi nguồn đã được nêu rõ ở câu ngay trước và cụm này chỉ tham chiếu lại.

## VI-HUM-D04: `meta-discourse-thua`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `paragraph` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Câu chỉ dẫn người đọc ("cần lưu ý rằng", "đáng chú ý là", "như đã đề cập") xuất hiện dày trong một đoạn mà không mang thông tin mới.
- Rewrite strategy:
  - Bỏ câu meta khi phần theo sau đã đủ rõ.
  - Chỉ giữ khi thực sự cần phân nhánh tài liệu dài.
- Good examples:
  - `clean_rewrite`: Hệ thống có 3 tầng. Tầng 2 xử lý dữ liệu.
    - Reason: Bỏ câu meta, giữ nguyên dữ kiện.
  - `no_change`: Như đã đề cập ở phần Kiến trúc, hệ thống dùng cache. Phần này mô tả cách cache hoạt động.
    - Reason: Câu meta dùng để liên kết phần cụ thể trong tài liệu dài.
- Exceptions:
  - Tài liệu dài, sách giáo trình, hoặc văn bản có phân nhánh cấu trúc cần câu dẫn.
  - Trích dẫn nguyên văn.

## VI-HUM-D05: `so-lieu-khong-nguon`

- Skill: `humanizer-vi`
- Finding type: `warning`
- Scope / aggregation: `sentence` / `count`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Số liệu hoặc tỉ lệ phần trăm xuất hiện nhiều lần trong văn bản mà câu chứa chúng không nêu nguồn hoặc dấu hiệu ước lượng.
- Rewrite strategy:
  - Nêu nguồn cụ thể nếu có.
  - Đánh dấu là ước lượng nếu không có nguồn.
  - Thu hẹp tuyên bố nếu con số không kiểm chứng được.
- Good examples:
  - `no_change`: Theo khảo sát nội bộ tháng 6, 70% người dùng hài lòng với sản phẩm.
    - Reason: Số liệu có nguồn rõ.
  - `no_change`: Tôi ước chừng khoảng 70% người dùng hài lòng.
    - Reason: Có dấu hiệu ước lượng.
- Exceptions:
  - Câu có nguồn cụ thể, hoặc dấu hiệu ước lượng rõ.
  - Số liệu trong biểu đồ/bảng có chú thích nguồn.

## VI-HUM-D06: `cam-xuc-phang`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `variance`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Văn bản nói về chủ đề cảm xúc mạnh nhưng giọng điệu không thay đổi — không có câu ngắn đột ngột, không có từ ngữ đời thường, không có sự im lặng.
- Rewrite strategy:
  - Cho phép một vài câu ngắn đột ngột khi nội dung chạm tới cảm xúc mạnh.
  - Thêm chi tiết cụ thể (không phải ví dụ mới) nếu câu chuyện có.
- Good examples:
  - `review_comment`: Cần xem lại giọng điệu — chủ đề là mất mát/khó khăn nhưng văn bản không có câu ngắn, từ ngữ đời thường, hay sự im lặng. Có thể thêm nhịp gãy khi cảm xúc lên cao.
    - Reason: Gợi ý reviewer xem lại, không tự viết lại câu.
  - `no_change`: Tôi vừa mất việc. Mấy hôm đầu tôi không biết làm gì. Sau đó tôi bắt đầu gửi CV, và dần thấy nhẹ hơn.
    - Reason: Chủ đề tiêu cực, giọng điệu chuyển dần, không phải văn AI phẳng.
- Exceptions:
  - Văn bản học thuật hoặc báo chí khách quan cố ý giữ giọng đều.
  - Văn bản có chủ đề cảm xúc nhưng register formal cần đều giọng.

## VI-HUM-D07: `cam-xuc-khong-nhat-quan`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `single`
- Severity / confidence: `low` / `low`
- False-positive risk: `medium`
- Tóm tắt: Nội dung nói điều buồn nhưng giọng văn vui, hoặc ngược lại — cảm xúc của nội dung và giọng văn không nhất quán.
- Rewrite strategy:
  - Điều chỉnh giọng văn cho khớp với nội dung.
  - Nếu có lý do nghệ thuật cho sự không nhất quán, làm rõ lý do đó trong câu.
- Good examples:
  - `clean_rewrite`: Tôi vừa mất việc. Tôi chưa biết phải làm gì tiếp theo.
    - Reason: Giọng văn khớp với nội dung tiêu cực.
  - `no_change`: Dự án thất bại. Chúng tôi mất ba tháng và một khoản ngân sách không nhỏ. Nhưng ít nhất giờ tôi biết cách nào không hiệu quả.
    - Reason: Nội dung tiêu cực, giọng chuyển dần sang trung tính hợp lý.
- Exceptions:
  - Văn trào phúng (satire) có chủ đích không nhất quán giữa nội dung và giọng.
  - Trích dẫn phản ứng của người khác.

## VI-HUM-D08: `echo-noi-dung`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `count`
- Severity / confidence: `low` / `low`
- False-positive risk: `medium`
- Tóm tắt: Cùng một ý được nói lại bằng từ khác ở các đoạn khác nhau, không phải lặp từ mà lặp ý niệm.
- Rewrite strategy:
  - Gộp các câu cùng ý thành một câu duy nhất.
  - Hoặc mở rộng ý đó bằng chi tiết mới thay vì lặp lại.
- Good examples:
  - `clean_rewrite`: Dự án cần thêm ngân sách để hoàn thành — cụ thể là khoảng 200 triệu cho giai đoạn hai.
    - Reason: Gộp ba câu thành một, thêm chi tiết cụ thể.
  - `no_change`: Dự án cần thêm ngân sách để hoàn thành. Đội ngũ cũng cần thêm hai kỹ sư.
    - Reason: Hai ý khác nhau, không echo.
- Exceptions:
  - Điệp ngữ (anaphora) có chủ đích trong văn nghị luận hoặc thơ.
  - Văn bản nhiều phần cố ý nhắc lại ý chính.

## VI-HUM-D09: `phan-xa-tra-loi-tron-ven`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `single`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Nếu văn bản bắt đầu bằng câu hỏi hoặc nhiệm vụ, nó trả lời đầy đủ + giải thích + ví dụ + kết luận — không có chỗ nào lệch khỏi câu hỏi.
- Rewrite strategy:
  - Cho phép văn bản dừng ở câu trả lời trực tiếp nếu không cần mở rộng.
  - Hoặc trả lời lệch nếu câu hỏi gợi ra hướng khác quan trọng hơn.
- Good examples:
  - `clean_rewrite`: Dự án thất bại vì thiếu ngân sách cho giai đoạn hai.
    - Reason: Trả lời trực tiếp, không mở rộng.
  - `no_change`: Làm thế nào để cải thiện quy trình? Câu hỏi hay. Nhưng trước khi trả lời, tôi cần biết quy trình hiện tại đang gặp vấn đề gì.
    - Reason: Không trả lời trực tiếp, hỏi ngược lại.
- Exceptions:
  - Văn bản học thuật có yêu cầu trả lời đầy đủ theo rubric.
  - Hướng dẫn kỹ thuật có cấu trúc cố định.

## VI-HUM-L01: `dong-vai-tro-trong-viec`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `phrase` / `density`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Lạm dụng cấu trúc "đóng vai trò ... trong việc" khi một động từ trực tiếp rõ hơn.
- Rewrite strategy:
  - Xác định hành động thật rồi đưa động từ đó lên làm vị ngữ chính.
  - Giữ mức độ quan trọng nếu văn bản có căn cứ cho đánh giá ấy.
- Good examples:
  - `clean_rewrite`: Tính năng này quan trọng đối với việc cải thiện hiệu suất.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Người quản lý có vai trò then chốt đối với việc duy trì tiến độ.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi văn bản thực sự phân tích vai trò của một người, bộ phận hoặc chức năng.

## VI-HUM-L02: `boi-canh-khong-ngung-phat-trien`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `paragraph` / `density`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Câu mở bằng "trong bối cảnh không ngừng phát triển" nhưng không nêu thay đổi cụ thể.
- Rewrite strategy:
  - Nêu thay đổi, mốc thời gian hoặc áp lực cụ thể; nếu không có thì bỏ lời dẫn.
- Good examples:
  - `clean_rewrite`: Doanh nghiệp cần đổi mới.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Kỹ năng số rất quan trọng.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi câu sau định nghĩa rõ xu hướng và lời dẫn giúp liên kết với đoạn trước.

## VI-HUM-L03: `loi-khen-chung-chung`

- Skill: `humanizer-vi`
- Finding type: `warning`
- Scope / aggregation: `paragraph` / `density`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Dùng nhiều lời khen như "đột phá" hoặc "vượt trội" mà không có căn cứ trong văn bản.
- Rewrite strategy:
  - Thay lời khen bằng đặc tính, kết quả hoặc bằng chứng đã có trong đầu vào.
- Good examples:
  - `review_comment`: Cần có tiêu chí so sánh trước khi gọi hiệu năng “vượt trội”; thông tin hiện có chỉ xác nhận công cụ xử lý 2.000 bản ghi mỗi phút trong thử nghiệm nội bộ.
    - Reason: Không xóa đánh giá của tác giả hoặc biến dữ kiện thành câu thay thế khi thiếu căn cứ.
  - `review_comment`: Cần có tiêu chí chất lượng trước khi gọi gói này “đẳng cấp”; thông tin hiện có chỉ xác nhận bảo hành 24 tháng và hỗ trợ trong giờ hành chính.
    - Reason: Không tự quyết định bỏ lập trường đánh giá khi chưa có bằng chứng.
- Exceptions:
  - Khi đây là trích dẫn, slogan đã duyệt hoặc lời đánh giá có nguồn và tiêu chí rõ.

## VI-HUM-L04: `mat-do-han-viet-sao-rong`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `paragraph` / `density`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Mật độ từ Hán-Việt sáo rỗng cao trong một đoạn văn, tạo giọng "văn AI" cứng nhắc.
- Rewrite strategy:
  - Thay thế bằng từ thuần Việt hoặc Hán-Việt phổ thông khi có lựa chọn tự nhiên hơn.
  - Giữ nguyên nếu từ đó là thuật ngữ chuyên ngành đã được định nghĩa.
- Good examples:
  - `clean_rewrite`: Chúng tôi phân tích thị trường, dùng nguồn lực sẵn có để cải thiện quy trình và giúp đội ngũ hiểu rõ hơn.
    - Reason: Giữ nguyên ý, thay từ sáo rỗng bằng từ tự nhiên.
  - `clean_rewrite`: Chúng tôi dùng tối đa nguồn lực hiện có để tăng giá trị và cải thiện hệ thống.
    - Reason: Thay cụm sáo rỗng bằng từ tự nhiên.
- Exceptions:
  - Văn bản pháp lý, hành chính cần giữ thuật ngữ Hán-Việt chính xác.
  - Trích dẫn nguyên văn.

## VI-HUM-L05: `lam-phat-khai-niem`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `phrase` / `count`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Danh từ cụ thể được bọc trong wrapper trừu tượng ("hành trình học tập", "trải nghiệm người dùng") khi từ gốc đã đủ nghĩa.
- Rewrite strategy:
  - Bỏ wrapper nếu danh từ gốc đã đủ nghĩa.
  - Giữ nếu wrapper thực sự là một khái niệm được định nghĩa trong tài liệu.
- Good examples:
  - `clean_rewrite`: Sản phẩm này dễ dùng. Việc học của sinh viên cần được tôn trọng.
    - Reason: Dùng thẳng danh từ cụ thể.
  - `no_change`: Trải nghiệm người dùng là thuật ngữ UX đo mức độ dễ dùng của sản phẩm.
    - Reason: Wrapper là thuật ngữ đã được định nghĩa.
- Exceptions:
  - Wrapper là thuật ngữ chuyên ngành đã định nghĩa (ví dụ trong glossary UX).
  - Trích dẫn nguyên văn hoặc slogan đã duyệt.

## VI-HUM-L06: `do-sau-gia`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `sentence` / `count`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Câu có cấu trúc "không phải X mà là Y" lặp lại như khuôn, tạo cảm giác sâu sắc mà không thêm dữ kiện.
- Rewrite strategy:
  - Nêu trực tiếp điểm chính.
  - Giữ cấu trúc đối lập khi thực sự có hai lựa chọn đối lập cần phân biệt.
- Good examples:
  - `review_comment`: Cần cụ thể hóa "hành trình" và "đích đến" là gì trước khi giữ cấu trúc đối lập; hiện tại cả hai đều trừu tượng.
    - Reason: Không tự thay câu của tác giả khi chưa rõ dữ kiện.
  - `no_change`: Dự án không phải là bản demo mà là sản phẩm hoàn chỉnh.
    - Reason: Hai lựa chọn cụ thể, đối lập rõ, không phải câu rỗng.
- Exceptions:
  - Hai nhánh X và Y đều có chi tiết cụ thể hoặc là thuật ngữ đã định nghĩa.
  - Trích dẫn nguyên văn, slogan.

## VI-HUM-L07: `do-tinh-vi-mo-coi`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `count`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Có ẩn dụ, so sánh, hoặc hình ảnh nhưng các câu xung quanh không "nuôi" ẩn dụ đó — ẩn dụ đứng một mình, mồ côi.
- Rewrite strategy:
  - Mở rộng ẩn dụ bằng cách cho các câu xung quanh liên quan tới nó.
  - Hoặc bỏ ẩn dụ nếu không thể triển khai.
- Good examples:
  - `clean_rewrite`: Dự án như con thuyền nhỏ giữa biển lớn: ngân sách là nhiên liệu, đội ngũ là thủy thủ, và sáu tháng là khoảng cách bờ.
    - Reason: Cả đoạn xoay quanh ẩn dụ.
  - `no_change`: Ngân sách đã được phê duyệt. Đội ngũ có mười thành viên. Thời hạn kéo dài sáu tháng.
    - Reason: Không có ẩn dụ — không có gì để nuôi.
- Exceptions:
  - Văn thơ hoặc văn nghệ thuật có ẩn dụ độc lập có chủ đích.
  - Slogan hoặc khẩu hiệu.

## VI-HUM-S01: `lap-cau-mo-dau-bang-viec`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `paragraph` / `sequence`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Nhiều câu liên tiếp trong cùng đoạn mở bằng cùng một từ, tạo nhịp đều.
- Rewrite strategy:
  - Đưa chủ thể hoặc động từ lên đầu; gộp câu khi chúng cùng một chủ thể.
- Good examples:
  - `clean_rewrite`: Cập nhật giúp giảm lỗi; kiểm thử giúp tăng độ ổn định.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Họp sớm là việc cần thiết; gửi tài liệu trước cũng quan trọng.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi "việc" gọi tên một hành vi đã được định nghĩa trong văn bản pháp lý hoặc phân tích.
  - Danh sách có chủ đích (gạch đầu dòng, đánh số) dùng cùng chủ thể.
  - Tín hiệu nằm ở các đoạn khác nhau.

## VI-HUM-S02: `khong-chi-ma-con-lap`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `paragraph` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `high`
- Tóm tắt: Lặp cấu trúc "không chỉ ... mà còn" để tạo nhấn mạnh cho các ý bình thường.
- Rewrite strategy:
  - Nêu trực tiếp hai tác động hoặc chọn tác động quan trọng hơn.
- Good examples:
  - `clean_rewrite`: Công cụ mở tệp 2 GB trong 4 giây và có phím tắt cho các thao tác chính.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Khóa học có sáu bài thực hành và một buổi phản biện.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi phép đối sánh là trọng tâm lập luận và không bị lặp trong đoạn.

## VI-HUM-S03: `tu-noi-day-dac`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `paragraph` / `density`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Dùng dày các từ nối "đồng thời", "qua đó" và "từ đó" dù quan hệ logic đã rõ.
- Rewrite strategy:
  - Giữ từ nối chỉ khi nó diễn đạt quan hệ logic cần thiết; tách câu nếu có quá nhiều mệnh đề.
- Good examples:
  - `clean_rewrite`: Hệ thống lưu log và gửi cảnh báo để giúp nhóm phản hồi, từ đó nâng cao chất lượng.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Nhóm sửa lỗi, cập nhật tài liệu và qua đó tạo ra giá trị.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `no_change`: Nhóm lưu log, đồng thời gửi cảnh báo. Qua đó quy trình rõ hơn. Từ đó chất lượng tăng.
    - Reason: Mỗi đoạn chỉ có một từ nối; không gộp tín hiệu xuyên đoạn.
  - `no_change`: - Nhóm lưu log, đồng thời gửi cảnh báo. - Qua đó, quy trình rõ hơn. - Từ đó, chất lượng tăng.
    - Reason: Danh sách có chủ đích; không gộp tín hiệu giữa các mục.
- Exceptions:
  - Khi phép đối sánh là trọng tâm lập luận và không bị lặp trong đoạn.
  - Tín hiệu nằm ở các đoạn khác nhau.
  - Danh sách có chủ đích (gạch đầu dòng, đánh số).

## VI-HUM-S04: `do-dai-cau-dong-deu`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `variance`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Năm câu trở lên có độ dài gần như nhau, tạo nhịp đều cần người viết đọc lại.
- Rewrite strategy:
  - Đọc thành tiếng và chỉ tách hoặc gộp nơi cấu trúc ý cần thay đổi.
- Good examples:
  - `clean_rewrite`: Nhóm nhận yêu cầu sáng nay, kiểm tra dữ liệu vào buổi trưa và sẽ gửi kết quả cuối ngày. Sau cuộc họp, nhóm lưu biên bản và đóng yêu cầu khi hoàn tất.
  - `clean_rewrite`: Máy chủ ghi log mỗi phút và hệ thống gửi báo cáo mỗi giờ. Nhân viên xem dashboard hằng ngày; bộ phận sao lưu dữ liệu mỗi tuần, còn quản lý rà báo cáo mỗi tháng.
- Exceptions:
  - Checklist, thông số kỹ thuật, văn bản cho người mới đọc hoặc nhịp lặp có chủ đích.

## VI-HUM-S05: `do-dai-cau-qua-deu`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `variance`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `high`
- Tóm tắt: Độ biến thiên độ dài câu thấp (burstiness thấp) – dấu hiệu thống kê mạnh của văn AI.
- Rewrite strategy:
  - Đa dạng hóa độ dài câu: tách câu dài thành câu ngắn, gộp câu ngắn thành câu dài.
  - Đọc thành tiếng và điều chỉnh nhịp điệu.
- Good examples:
  - `clean_rewrite`: Hệ thống mới giúp giảm thời gian xử lý và tăng độ chính xác. Người dùng thao tác nhanh hơn; quản trị viên giám sát dễ hơn. Tất cả tính năng đều ổn định.
    - Reason: Xen kẽ câu ngắn và dài, tạo nhịp tự nhiên hơn.
  - `clean_rewrite`: Quy trình cập nhật thường xuyên, tài liệu đầy đủ. Nhân viên đào tạo định kỳ, kết quả đánh giá hàng quý. Chất lượng cải thiện liên tục.
    - Reason: Xen kẽ câu ngắn và dài, tránh nhịp đều đều.
- Exceptions:
  - Checklist, danh sách có cấu trúc cố định.
  - Văn bản kỹ thuật cần độ chính xác cao.

## VI-HUM-S07: `doan-deu-cau`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `variance`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Năm đoạn trở lên có số câu gần bằng nhau, tạo cấu trúc đoạn đều đặn cần người viết đọc lại.
- Rewrite strategy:
  - Đọc lại từng đoạn và chỉ tách hoặc gộp khi cấu trúc ý cần thay đổi.
  - Cho phép một vài đoạn rất ngắn nếu ý không cần triển khai.
- Good examples:
  - `clean_rewrite`: Đoạn ngắn. Đoạn dài có nhiều câu liên tiếp. Câu hai dài hơn. Câu ba cũng vậy. Câu bốn nữa. Câu năm tiếp theo. Câu sáu vẫn dài. Câu bảy kết thúc đoạn. Đoạn ba câu. Câu hai. Câu ba. Đoạn bốn có năm câu. Câu hai. Câu ba. Câu bốn. Câu năm. Đoạn năm có bảy câu. Câu hai. Câu ba. Câu bốn. Câu năm. Câu sáu. Câu bảy.
    - Reason: Đoạn dài ngắn xen kẽ, cấu trúc biến thiên.
  - `no_change`: Checklist: - Mục một. - Mục hai. - Mục ba.
    - Reason: Cấu trúc danh sách có chủ đích, không phải văn xuôi.
- Exceptions:
  - Checklist, thông số kỹ thuật, văn bản có cấu trúc do hệ thống sinh.
  - Văn bản có quy định mỗi mục một đoạn ngắn (thông báo hành chính).

## VI-HUM-S08: `hedge-rai-deu`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `variance`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Hedge ("có lẽ", "dường như", "có khả năng") rải đều khắp mọi đoạn thay vì tập trung ở chỗ thật sự cần.
- Rewrite strategy:
  - Tập trung hedge ở chỗ thực sự cần bảo vệ nhận định.
  - Khẳng định trực tiếp ở chỗ có đủ căn cứ.
- Good examples:
  - `clean_rewrite`: Kết quả rõ ràng. Số liệu xác nhận. Phân tích chặt chẽ. Tuy nhiên có lẽ cần kiểm chứng thêm. Có khả năng sai lệch. Dường như chưa đủ mẫu. Kết luận khẳng định. Số liệu ủng hộ. Phân tích đầy đủ. Báo cáo hoàn tất. Nhóm đã xác nhận. Không có sai sót. Kết quả cuối cùng rõ ràng. Số liệu đã kiểm tra. Phân tích nhất quán.
    - Reason: Hedge tập trung ở đoạn hai; các đoạn khác khẳng định trực tiếp.
  - `no_change`: Có lẽ dự án sẽ trễ. Dường như tiến độ chậm. Có khả năng cần gia hạn.
    - Reason: Hedge tập trung trong một đoạn ngắn cho một nhận định rủi ro.
- Exceptions:
  - Văn bản khoa học cần nhiều hedge để thể hiện giới hạn của nghiên cứu.
  - Trích dẫn nguyên văn.

## VI-HUM-S09: `lien-ke-nhanh-khong-chi-tiet`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Cấu trúc "về mặt X" hoặc "khía cạnh Y" lặp lại để liệt kê nhanh nhiều khía cạnh mà không đi sâu vào khía cạnh nào.
- Rewrite strategy:
  - Chọn khía cạnh quan trọng nhất và triển khai sâu.
  - Nếu thực sự cần liệt kê nhiều khía cạnh, bổ sung chi tiết cụ thể cho mỗi khía cạnh.
- Good examples:
  - `clean_rewrite`: Dự án có tiềm năng kinh tế; cụ thể, ước tính hoàn vốn sau 18 tháng với doanh thu tăng 15% mỗi quý.
    - Reason: Tập trung vào một khía cạnh và đi sâu với dữ kiện.
  - `no_change`: Về mặt tài chính, dự án cần thêm 2 tỷ đồng cho giai đoạn hai, dự kiến hoàn vốn sau 18 tháng.
    - Reason: Một khía cạnh duy nhất, có chi tiết cụ thể.
- Exceptions:
  - Văn bản so sánh có mục đích liệt kê cân bằng các khía cạnh với chi tiết cho mỗi mục.
  - Trích dẫn nguyên văn hoặc báo cáo chính thức có quy định cấu trúc.

## VI-HUM-S10: `doi-xung-so-muc`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `single`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Số lượng mục tích cực và tiêu cực bằng nhau một cách đối xứng ("3 ưu điểm và 3 nhược điểm").
- Rewrite strategy:
  - Cho phép số mục hai nhánh khác nhau nếu vấn đề không thực sự cân.
  - Bổ sung chi tiết cho mỗi nhánh thay vì đếm số mục.
- Good examples:
  - `no_change`: Phân tích cho thấy 3 ưu điểm và 5 nhược điểm của phương án.
    - Reason: Số mục hai nhánh khác nhau, phản ánh thực tế.
  - `no_change`: Báo cáo liệt kê nhiều lợi ích và một số hạn chế của chính sách.
    - Reason: Không đếm số cụ thể, tránh khuôn đối xứng.
- Exceptions:
  - Văn bản so sánh có yêu cầu đối xứng theo quy định (ví dụ bảng so sánh có số dòng bằng nhau).
  - Đề bài yêu cầu liệt kê cùng số mục.

## VI-HUM-S11: `noi-nhan-qua-day-dac`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Từ nối nhân quả ("do đó", "bởi vậy", "kết quả là", "dẫn đến") xuất hiện dày trong văn bản.
- Rewrite strategy:
  - Giữ từ nối chỉ khi quan hệ nhân quả thực sự rõ.
  - Bỏ từ nối khi hai ý chỉ đứng cạnh nhau mà không nhân quả.
- Good examples:
  - `clean_rewrite`: Hệ thống chậm khiến người dùng phàn nàn, nên nhóm phải họp và lùi deadline.
    - Reason: Rút gọn từ nối, giữ quan hệ nhân quả chính.
  - `no_change`: Do đó, quyết định cuối cùng vẫn là chờ thêm dữ liệu.
    - Reason: Một từ nối nhân quả cho quan hệ rõ.
- Exceptions:
  - Văn bản phân tích nhân quả chặt chẽ có mục đích lập luận.
  - Trích dẫn nguyên văn.

## VI-HUM-S12: `tu-noi-chuyen-y-day-dac`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `paragraph` / `density`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Từ nối chuyển ý ("tuy nhiên", "bên cạnh đó", "hơn nữa") xuất hiện dày trong một đoạn dù ý đã liên kết tự nhiên.
- Rewrite strategy:
  - Giữ từ nối chỉ khi quan hệ logic cần thiết.
  - Bỏ từ nối khi ý đã liên kết tự nhiên.
- Good examples:
  - `clean_rewrite`: Hệ thống còn lỗi, hiệu năng chưa tốt và tài liệu còn thiếu.
    - Reason: Bỏ từ nối, gộp ý liên kết tự nhiên.
  - `no_change`: Tuy nhiên, dự án vẫn còn rủi ro.
    - Reason: Một từ nối chuyển ý cho quan hệ tương phản rõ ràng.
- Exceptions:
  - Đoạn có ≥5 câu và mỗi từ nối đánh dấu quan hệ khác nhau.
  - Danh sách có chủ đích (gạch đầu dòng, đánh số).

## VI-HUM-S13: `dong-kin-ngu-nghia`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `variance`
- Severity / confidence: `low` / `low`
- False-positive risk: `medium`
- Tóm tắt: Hầu hết các đoạn kết bằng câu tóm tắt hoặc kết luận — văn bản không có chỗ "mở" nào, không có câu hỏi bỏ lửng, không có ý chưa hoàn thành.
- Rewrite strategy:
  - Cho phép một vài đoạn kết bằng câu hỏi hoặc chi tiết cụ thể thay vì tóm tắt.
  - Không cần kết luận cho mọi đoạn nếu ý đã rõ.
- Good examples:
  - `clean_rewrite`: Đoạn một bàn về vấn đề A. Đoạn hai phân tích vấn đề B. Tại sao B lại quan trọng hơn A? Đoạn ba đề cập vấn đề C.
    - Reason: Có đoạn kết bằng câu hỏi, không phải tóm tắt.
  - `no_change`: Bước một là chuẩn bị. Bước hai là triển khai. Cái khó là ở đây. Bước ba là kiểm tra.
    - Reason: Đoạn hai kết bằng chi tiết cụ thể, không phải tóm tắt.
- Exceptions:
  - Văn bản học thuật hoặc báo cáo chính thức có quy định mỗi đoạn kết bằng tóm tắt.
  - Trích dẫn hoặc mục lục có cấu trúc cố định.

## VI-HUM-S14: `liet-ke-thu-tu-day-dac`

- Skill: `humanizer-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Dùng dày "thứ nhất/thứ hai/thứ ba" hoặc các biến thể liệt kê để chia ý, dấu hiệu listification của văn AI.
- Rewrite strategy:
  - Chỉ giữ marker khi thứ tự thật sự quan trọng.
  - Bỏ marker ở các ý có thể liệt kê tự nhiên.
  - Đa dạng hóa cách liên kết ý thay vì thuần "thứ nhất... thứ hai... thứ ba".
- Good examples:
  - `clean_rewrite`: Dự án thất bại. Ngân sách không đủ, đội ngũ thiếu người, và kế hoạch không rõ.
    - Reason: Bỏ markers, giữ nguyên nội dung.
  - `no_change`: Có hai điểm cần lưu ý. Thứ nhất là deadline tháng 8 không thể dời. Thứ hai, ngân sách đã chốt từ tháng 6.
    - Reason: Chỉ 2 markers, dưới ngưỡng.
- Exceptions:
  - Quy trình, luật, hướng dẫn kỹ thuật cần liệt kê theo thứ tự.
  - Đề bài yêu cầu rõ "liệt kê 3 điểm".

## VI-STY-C01: `viet-hoa-danh-tu-chung`

- Skill: `style-guide-vi`
- Finding type: `preference`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Danh từ chung, khái niệm trừu tượng, chức danh hoặc đại từ bị viết hoa giữa câu để tạo vẻ trang trọng.
- Rewrite strategy:
  - Viết thường danh từ chung, trừ tên riêng, thuật ngữ pháp lý đã định nghĩa hoặc style thương hiệu.
- Good examples:
  - `clean_rewrite`: Chúng tôi cung cấp giải pháp cho mọi khách hàng.
  - `clean_rewrite`: Sản phẩm này đi kèm dịch vụ bảo hành.
- Exceptions:
  - Tên thương hiệu, nhãn UI, thuật ngữ đã định nghĩa trong hợp đồng hoặc style guide yêu cầu.

## VI-STY-C02: `title-case-nhiem-tieng-anh`

- Skill: `style-guide-vi`
- Finding type: `preference`
- Scope / aggregation: `document` / `count`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Hai hoặc nhiều cụm từ viết hoa chữ đầu (Title Case) xuất hiện giữa câu, dấu hiệu nhiễm quy ước tiếng Anh hoặc over-generalize viết hoa để nhấn mạnh.
- Rewrite strategy:
  - Viết thường các cụm Title Case giữa câu, trừ khi là tên riêng.
  - Nếu cụm là tiêu đề thực sự, chuyển thành heading Markdown thay vì viết hoa giữa câu.
- Good examples:
  - `clean_rewrite`: Chúng tôi tập trung vào trải nghiệm người dùng và tầm nhìn chiến lược.
    - Reason: Viết thường các cụm danh từ chung.
  - `no_change`: Tôi đi từ Hà Nội đến Hồ Chí Minh tuần trước.
    - Reason: Các cụm là tên riêng địa danh.
  - `no_change`: Đoạn văn có nhiều câu. Báo Cáo Kinh Doanh là từ viết hoa ở đầu câu thứ hai.
    - Reason: Cụm Title Case nằm ở đầu câu, không tính.
- Exceptions:
  - Tên riêng, địa danh, quốc gia, tổ chức.
  - Tiêu đề Markdown bắt đầu bằng dấu
  - Đoạn văn trong ngoặc kép hoặc code block.
  - Trích dẫn nguyên văn từ tiếng Anh.

## VI-STY-F01: `heading-qua-day`

- Skill: `style-guide-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `density`
- Severity / confidence: `low` / `medium`
- False-positive risk: `high`
- Tóm tắt: Dùng nhiều heading cho các phần chỉ có một câu ngắn, làm cấu trúc tài liệu bị vụn.
- Rewrite strategy:
  - Gộp các mục cùng chủ đề thành đoạn hoặc danh sách; giữ heading khi nó giúp điều hướng tài liệu dài.
- Good examples:
  - `clean_rewrite`: Trang tải nhanh; dữ liệu được mã hóa.
  - `clean_rewrite`: 1. Nhập email. 2. Nhập mật khẩu.
- Exceptions:
  - Reference tra cứu nhanh, FAQ, UI copy inventory hoặc cấu trúc do hệ thống sinh.

## VI-STY-F02: `in-dam-co-hoc`

- Skill: `style-guide-vi`
- Finding type: `heuristic`
- Scope / aggregation: `document` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `high`
- Tóm tắt: Nhiều bullet mở bằng nhãn in đậm và dấu hai chấm dù nội dung có thể viết thành câu hoặc bảng.
- Rewrite strategy:
  - Giữ nhãn khi người đọc cần quét; nếu không, viết bullet trực tiếp hoặc dùng bảng.
- Good examples:
  - `clean_rewrite`: - Trang tải nhanh. - Dữ liệu được mã hóa.
  - `clean_rewrite`: 1. Mở file. 2. Chọn Lưu.
- Exceptions:
  - Glossary, danh sách thuộc tính, changelog hoặc nội dung cần quét nhanh theo nhãn.

## VI-STY-N01: `don-vi-khong-co-khoang-trang`

- Skill: `style-guide-vi`
- Finding type: `preference`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Số và ký hiệu đơn vị viết liền trong văn bản khi style dự án yêu cầu một khoảng trắng.
- Rewrite strategy:
  - Theo style guide; mặc định thêm một khoảng trắng giữa số và đơn vị trong văn bản.
- Good examples:
  - `clean_rewrite`: Tệp có dung lượng 5 GB.
  - `clean_rewrite`: Mẫu được giữ ở 4 °C.
- Exceptions:
  - Nhãn UI thiếu chỗ, quy ước ngành, code, identifier hoặc style guide yêu cầu viết liền.

## VI-STY-N02: `phan-tram-khong-nhat-quan`

- Skill: `style-guide-vi`
- Finding type: `preference`
- Scope / aggregation: `document` / `consistency`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Trộn dạng phần trăm có và không có khoảng trắng trong cùng tài liệu.
- Rewrite strategy:
  - Chọn dạng theo style guide và áp cho văn bản thường, không sửa dữ liệu hoặc code.
- Good examples:
  - `clean_rewrite`: Tỷ lệ A là 15%, còn tỷ lệ B là 20%.
  - `clean_rewrite`: Chiết khấu 5% được dùng ở cả bảng và phần mô tả.
- Exceptions:
  - Trích dẫn, dữ liệu nhập, locale khác nhau hoặc style từng sản phẩm có chủ đích.

## VI-STY-N03: `ngay-thang-mo-ho`

- Skill: `style-guide-vi`
- Finding type: `warning`
- Scope / aggregation: `token` / `single`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Ngày viết dạng số ngắn có thể bị hiểu theo thứ tự ngày-tháng hoặc tháng-ngày.
- Rewrite strategy:
  - Dùng tên tháng, ISO 8601 hoặc nêu locale theo style guide.
- Good examples:
  - `clean_rewrite`: Hạn chót là ngày 7 tháng 8 năm 2026.
    - Context: Tài liệu dùng thứ tự ngày/tháng/năm.
  - `needs_author_decision`: Cần xác nhận “26” thuộc thế kỷ nào trước khi đổi định dạng ngày.
- Exceptions:
  - Tài liệu nội bộ có locale đã công bố, dữ liệu máy hoặc biểu mẫu bắt buộc.

## VI-STY-P01: `xung-ho-khong-nhat-quan`

- Skill: `style-guide-vi`
- Finding type: `warning`
- Scope / aggregation: `document` / `consistency`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `high`
- Tóm tắt: Trộn nhiều cách gọi độc giả hoặc người viết mà chưa có lý do chức năng.
- Rewrite strategy:
  - Xác định quan hệ với độc giả rồi lập bảng cách gọi; giữ thuật ngữ phân tích khi nó có chức năng riêng.
- Good examples:
  - `clean_rewrite`: Bạn chọn gói rồi xác nhận địa chỉ.
    - Context: Style guide quy định gọi độc giả là “bạn”.
  - `needs_author_decision`: Cần xác nhận “chúng ta” có bao gồm người đọc hay chỉ phía “chúng tôi” trước khi sửa câu.
  - `no_change`: Bạn có thể mời người dùng mới vào workspace.
    - Reason: Bạn gọi độc giả, còn người dùng là đối tượng được nói tới.
- Exceptions:
  - Khi "người dùng" hoặc "khách hàng" là đối tượng phân tích còn "bạn" là lời gọi trực tiếp, hoặc trích dẫn nhiều người nói. Không suy ra thiếu nhất quán chỉ vì hai cụm cùng xuất hiện.

## VI-STY-P02: `chung-ta-ep-dong-thuan`

- Skill: `style-guide-vi`
- Finding type: `warning`
- Scope / aggregation: `sentence` / `single`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Dùng "chúng ta đều" để trình bày một nhận định như thể người đọc đã đồng ý.
- Rewrite strategy:
  - Nêu nhận định và căn cứ trực tiếp; chỉ dùng "chúng ta" khi nhóm bao gồm người đọc thật sự rõ.
- Good examples:
  - `clean_rewrite`: AI sẽ thay đổi mọi ngành.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Quy trình này rất đơn giản.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Lời nói trong nhóm đã có đồng thuận hoặc hoạt động hướng dẫn thật sự cùng làm.

## VI-STY-T01: `login-dang-nhap-lan-lon`

- Skill: `style-guide-vi`
- Finding type: `warning`
- Scope / aggregation: `document` / `consistency`
- Severity / confidence: `low` / `medium`
- False-positive risk: `high`
- Tóm tắt: Trộn "login", "log in" và "đăng nhập" cho cùng một thao tác trong nội dung người dùng.
- Rewrite strategy:
  - Theo glossary hoặc nhãn UI; không đổi tên API, command hay identifier.
- Good examples:
  - `clean_rewrite`: Chọn Đăng nhập, sau đó đăng nhập bằng email.
    - Context: Style guide quy định nhãn UI là “Đăng nhập”.
  - `clean_rewrite`: Nếu đăng nhập lỗi, hãy mở lại trang Đăng nhập.
    - Context: Style guide quy định dùng “đăng nhập” trong nội dung người dùng.
- Exceptions:
  - Khi phân biệt nhãn UI, endpoint, sự kiện analytics hoặc trích dẫn nguyên văn.

## VI-STY-T02: `viet-tat-chua-giai-thich`

- Skill: `style-guide-vi`
- Finding type: `warning`
- Scope / aggregation: `document` / `single`
- Severity / confidence: `low` / `low`
- False-positive risk: `high`
- Tóm tắt: Từ viết tắt in hoa xuất hiện trong nội dung phổ thông mà có thể chưa được giải thích.
- Rewrite strategy:
  - Giải thích ở lần đầu theo glossary; bỏ qua tên sản phẩm, đơn vị và từ viết tắt phổ biến với độc giả.
- Good examples:
  - `clean_rewrite`: Thỏa thuận mức dịch vụ (SLA) sẽ được rà trong cuộc họp.
    - Context: Glossary định nghĩa SLA là “thỏa thuận mức dịch vụ”.
  - `clean_rewrite`: Mục tiêu thời gian khôi phục (RTO) được dùng để quyết định phương án khôi phục.
    - Context: Glossary định nghĩa RTO là “mục tiêu thời gian khôi phục”.
  - `no_change`: Thỏa thuận mức dịch vụ (SLA) được nêu ở đầu. SLA vẫn được rà trong cuộc họp.
    - Reason: Lần xuất hiện sau đã có định nghĩa trước đó trong cùng tài liệu.
- Exceptions:
  - Từ viết tắt quen thuộc với độc giả, tên sản phẩm, đơn vị, code, bảng glossary, nội dung chuyên gia, hoặc acronym đã được giải thích trước đó trong cùng tài liệu.

## VI-TRA-L01: `mo-khoa-tiem-nang`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Dịch sát "unlock potential" thành "mở khóa tiềm năng" khi ý thực là cho phép hoặc cải thiện một khả năng cụ thể.
- Rewrite strategy:
  - Nêu khả năng, đối tượng và tác động cụ thể đã có trong bản gốc.
- Good examples:
  - `clean_rewrite`: Công cụ giúp tìm xu hướng trong dữ liệu bán hàng.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Khóa học phát triển năng lực lãnh đạo qua bài tập giao việc và phản hồi.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Slogan đã duyệt hoặc ngữ cảnh cố ý dùng ẩn dụ về khóa.

## VI-TRA-L02: `dieu-huong-su-phuc-tap`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Dịch "navigate complexity" thành "điều hướng sự phức tạp" thay vì nêu công việc cần xử lý.
- Rewrite strategy:
  - Thay bằng xử lý, theo dõi, lựa chọn hoặc đáp ứng tùy hành động gốc.
- Good examples:
  - `clean_rewrite`: Nền tảng giúp doanh nghiệp theo dõi các yêu cầu tuân thủ.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Hướng dẫn giải thích cách khai và nộp thuế hộ kinh doanh.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Văn cảnh nói thật về điều hướng trong không gian hoặc giao diện.

## VI-TRA-L03: `tac-dong-co-y-nghia`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Dịch "meaningful impact" thành "tác động có ý nghĩa" mà không nêu tác động cụ thể.
- Rewrite strategy:
  - Nêu thay đổi có thể quan sát hoặc giữ mức khái quát nếu bản gốc không có thêm dữ kiện.
- Good examples:
  - `clean_rewrite`: Chương trình hỗ trợ thiết thực bằng cách cấp học bổng cho 35 học sinh trong năm 2025.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Mỗi 200.000 đồng đóng góp tạo hỗ trợ thiết thực bằng cách chi trả một bộ sách.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi đây là thuật ngữ được định nghĩa bằng tiêu chí ở phần trước.

## VI-TRA-L04: `o-cap-do-cot-loi`

- Skill: `translationese-cleaner-vi`
- Finding type: `preference`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `low` / `high`
- False-positive risk: `low`
- Tóm tắt: Dịch "at its core" thành "ở cấp độ cốt lõi" như một lời dẫn tạo vẻ sâu sắc.
- Rewrite strategy:
  - Bỏ lời dẫn hoặc nêu thành phần nền tảng bằng danh từ cụ thể.
- Good examples:
  - `clean_rewrite`: Sản phẩm này là một nền tảng dữ liệu.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Vấn đề chính nằm ở cách hai nhóm trao đổi yêu cầu.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Phân tích kiến trúc có nhiều lớp và "lõi" là một thành phần đã định nghĩa.

## VI-TRA-L05: `tan-dung-moi-ngu-canh`

- Skill: `translationese-cleaner-vi`
- Finding type: `preference`
- Scope / aggregation: `phrase` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Dùng "tận dụng" cho mọi trường hợp của "leverage" dù động từ cụ thể tự nhiên hơn.
- Rewrite strategy:
  - Chọn dùng, phân tích, kết hợp, dựa vào hoặc khai thác theo quan hệ thực tế.
- Good examples:
  - `clean_rewrite`: Nhóm dùng AI để viết báo cáo.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Ứng dụng dùng nền tảng để gửi thông báo.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi nghĩa thực là khai thác lợi thế hoặc nguồn lực sẵn có.

## VI-TRA-L06: `trai-nghiem-lien-mach`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `low` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Dịch "seamless experience" thành "trải nghiệm liền mạch" mà không chỉ ra sự gián đoạn được loại bỏ.
- Rewrite strategy:
  - Mô tả bước chuyển, thời gian chờ hoặc thao tác được bỏ nếu đầu vào có dữ kiện.
- Good examples:
  - `clean_rewrite`: Việc chỉ đăng nhập một lần trên web và di động giúp trải nghiệm không bị gián đoạn.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Bản nháp được giữ khi người dùng đổi thiết bị, nên quá trình làm việc không bị gián đoạn.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi "liền mạch" là thuật ngữ UX đã có tiêu chí hoặc bằng chứng ở phần trước.

## VI-TRA-L07: `cau-truc-tieng-anh-dich-sat`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `sentence` / `count`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Cấu trúc câu tiếng Anh dịch sát sang tiếng Việt, tạo câu dài và cứng.
- Rewrite strategy:
  - Rút gọn cấu trúc dịch sát thành cấu trúc tiếng Việt trực tiếp.
  - Tách câu dài thành câu ngắn.
- Good examples:
  - `clean_rewrite`: Nhờ đó, chúng ta hiểu rõ hơn về vấn đề. Điều này quan trọng vì vài lý do. Để cải thiện quy trình, chúng ta cần xem xét nhiều yếu tố.
    - Reason: Rút gọn cấu trúc, giữ nguyên ý.
  - `clean_rewrite`: Với thị trường hiện tại, chúng ta hiểu rõ hơn về động lực cạnh tranh.
    - Reason: Rút gọn cấu trúc dịch sát, giữ nguyên ý.
- Exceptions:
  - Trích dẫn nguyên văn từ tiếng Anh.
  - Thuật ngữ chuyên ngành có cấu trúc cố định.

## VI-TRA-L08: `thoi-gian-mo-ho`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `document` / `count`
- Severity / confidence: `medium` / `high`
- False-positive risk: `medium`
- Tóm tắt: Cụm chỉ thời gian chung chung ("trong thời gian gần đây", "hiện nay") xuất hiện dày thay vì mốc cụ thể.
- Rewrite strategy:
  - Thay bằng mốc cụ thể nếu có.
  - Bỏ cụm khi câu sau đã ngụ ý thời gian.
- Good examples:
  - `clean_rewrite`: Từ quý 2 năm 2025, thị trường thay đổi và người dùng đòi hỏi cao hơn.
    - Reason: Thay cụm mơ hồ bằng mốc cụ thể.
  - `no_change`: Trong bối cảnh hiện tại của dự án, deadline tháng 8 là cố định.
    - Reason: Cụm thời gian dùng để neo bối cảnh cụ thể của dự án.
- Exceptions:
  - Cụm thời gian đi kèm mốc cụ thể trong cùng câu.
  - Trích dẫn nguyên văn.

## VI-TRA-S01: `thong-qua-viec-day-dac`

- Skill: `translationese-cleaner-vi`
- Finding type: `preference`
- Scope / aggregation: `phrase` / `count`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Lặp "thông qua việc" để dịch cấu trúc "by + V-ing" thay vì dùng động từ trực tiếp.
- Rewrite strategy:
  - Đưa hành động sau "việc" thành động từ chính hoặc mệnh đề chỉ cách thức.
- Good examples:
  - `clean_rewrite`: Hệ thống tự kiểm tra dữ liệu để giảm lỗi.
  - `clean_rewrite`: Nhóm dùng mẫu có sẵn để tiết kiệm thời gian.
- Exceptions:
  - Khi cần nhấn mạnh cơ chế và cấu trúc không bị lặp trong đoạn.

## VI-TRA-S02: `thuc-hien-viec`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Dùng động từ nhẹ "thực hiện việc" hoặc "tiến hành thực hiện" trước một hành động rõ.
- Rewrite strategy:
  - Biến danh từ chỉ hành động thành động từ chính, giữ chủ thể và thời gian.
- Good examples:
  - `clean_rewrite`: Nhóm đánh giá hồ sơ vào thứ Hai.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Kỹ thuật viên kiểm tra máy.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi "việc" là một đối tượng pháp lý đã được định nghĩa và cần tham chiếu nhất quán.

## VI-TRA-S03: `bi-dong-che-tac-nhan`

- Skill: `translationese-cleaner-vi`
- Finding type: `preference`
- Scope / aggregation: `sentence` / `count`
- Severity / confidence: `medium` / `low`
- False-positive risk: `high`
- Tóm tắt: Dùng "được ... bởi" theo tiếng Anh khi tác nhân đã rõ và cần chịu trách nhiệm.
- Rewrite strategy:
  - Đưa tác nhân lên làm chủ ngữ nếu trách nhiệm hoặc hành động là thông tin chính.
- Good examples:
  - `clean_rewrite`: Giám đốc phê duyệt báo cáo vào sáng nay.
  - `clean_rewrite`: Nhóm vận hành phát hiện lỗi trong ca đêm.
- Exceptions:
  - Khi tác nhân không biết, không quan trọng, cần giấu hợp lý hoặc phương pháp khoa học ưu tiên đối tượng.

## VI-TRA-S04: `dua-ra-su-ho-tro`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `phrase` / `single`
- Severity / confidence: `medium` / `high`
- False-positive risk: `low`
- Tóm tắt: Dùng "đưa ra/cung cấp sự hỗ trợ" thay cho động từ "hỗ trợ" trong câu thông thường.
- Rewrite strategy:
  - Dùng "hỗ trợ" làm động từ và giữ rõ người hỗ trợ, đối tượng, phạm vi.
- Good examples:
  - `clean_rewrite`: Nhóm sẽ hỗ trợ khách hàng mới.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
  - `clean_rewrite`: Bộ phận IT hỗ trợ trong giờ làm việc.
    - Reason: Giữ các dữ kiện đã có và chỉ sửa cấu trúc mục tiêu.
- Exceptions:
  - Khi "gói hỗ trợ" hoặc "sự hỗ trợ" là danh mục, quyền lợi hay đối tượng đang được phân tích.

## VI-TRA-S05: `cum-hanh-chinh-day-dac`

- Skill: `translationese-cleaner-vi`
- Finding type: `warning`
- Scope / aggregation: `sentence` / `count`
- Severity / confidence: `medium` / `medium`
- False-positive risk: `medium`
- Tóm tắt: Một câu chồng nhiều lớp diễn đạt hành chính thay cho các động từ trực tiếp.
- Rewrite strategy:
  - Nêu chủ thể và dùng động từ chính như "rà soát", "đánh giá" hoặc "kiểm tra"; đổi "nhằm mục đích" thành "để" khi nghĩa không đổi.
- Good examples:
  - `clean_rewrite`: Nhóm rà soát và đánh giá hệ thống.
  - `clean_rewrite`: Nhóm đánh giá rồi kiểm tra hệ thống.
- Exceptions:
  - Văn bản pháp lý cần giữ nguyên tên thủ tục hoặc trích dẫn biểu mẫu chính thức.

## VI-TRA-S06: `lam-dung-cac-va-nhung`

- Skill: `translationese-cleaner-vi`
- Finding type: `preference`
- Scope / aggregation: `paragraph` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `high`
- Tóm tắt: Lạm dụng "các" và "những" trước danh từ số nhiều khi ngữ cảnh đã rõ.
- Rewrite strategy:
  - Lược bỏ "các" hoặc "những" khi ngữ cảnh đã xác định số nhiều.
  - Giữ lại khi cần nhấn mạnh số lượng hoặc phân biệt với danh từ số ít.
- Good examples:
  - `clean_rewrite`: Giải pháp này giúp doanh nghiệp nâng cao chỉ số hiệu suất của đội ngũ, đồng thời tạo cơ hội mới cho nhân viên có năng lực.
    - Reason: Lược bỏ "các"/"những" thừa.
  - `clean_rewrite`: Cơ hội mới sẽ mở ra cho nhân viên có năng lực trong dự án sắp tới.
    - Reason: Lược bỏ "các"/"những" thừa.
- Exceptions:
  - Cần phân biệt rõ số ít/số nhiều trong ngữ cảnh pháp lý.
  - Danh từ không đếm được.

## VI-TRA-S07: `lam-dung-tro-tu-thoi-gian`

- Skill: `translationese-cleaner-vi`
- Finding type: `preference`
- Scope / aggregation: `paragraph` / `count`
- Severity / confidence: `low` / `medium`
- False-positive risk: `high`
- Tóm tắt: Lạm dụng "đã", "đang", "sẽ" khi ngữ cảnh thời gian đã rõ.
- Rewrite strategy:
  - Lược bỏ "đã"/"đang"/"sẽ" khi ngữ cảnh đã xác định thời gian.
  - Giữ lại khi cần nhấn mạnh sự tương phản thời gian.
- Good examples:
  - `clean_rewrite`: Chúng tôi cải tiến và triển khai. Thời gian tới, phạm vi mở rộng và áp dụng cho toàn bộ hệ thống.
    - Reason: Lược bỏ trợ từ thừa; ngữ cảnh đã rõ thời gian.
  - `clean_rewrite`: Chúng tôi đã triển khai và tiếp tục mở rộng. Đội ngũ phối hợp và bàn giao vào tuần sau.
    - Reason: Lược bỏ trợ từ thừa, giữ nguyên ý.
- Exceptions:
  - Cần phân biệt rõ thời gian trong tường thuật.
  - Câu điều kiện.

Tổng cộng: **69 pattern**.
