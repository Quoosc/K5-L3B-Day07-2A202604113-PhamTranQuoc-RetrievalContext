# Trạng thái kiểm chứng nguồn v3

**Nguồn đã được tác giả xác nhận**, theo [biên bản ngày 16/11/2026](../../artifacts/source-verification.json). Xác nhận bao gồm toàn bộ vùng nguồn của PDF Landsat 8 v5.0. Không có bước chờ tác giả xác nhận lại nguồn.

86 câu dev kế thừa nguyên nội dung các benchmark cũ. Một số trường `reviewer`, `review_reason` và cảnh báo của validator ghi trạng thái lúc tạo dữ liệu cũ. Chúng được giữ nguyên byte để truy vết thí nghiệm; trạng thái kiểm chứng hiện hành nằm trong biên bản trên và [kết quả validation kèm xác nhận](../../artifacts/benchmark-validation.json). Các cảnh báo đó không phải yêu cầu phê duyệt còn thiếu.

30 câu test mới được soạn từ bản gốc trước mọi lượt chạy v3. Catalog v7 được xây trước benchmark, không đọc câu hỏi/gold. Runtime đọc câu hỏi và nguồn; chỉ băm gold để kiểm lock, không đưa đáp án hoặc vùng chuẩn vào context. Khi review đầu ra, Codex ghi rõ vai trò hỗ trợ đối chiếu; không gán việc đọc các output mới cho tác giả hoặc một người chấm bên ngoài.

Xác nhận nguồn không thay đổi đáp án model, verdict, lỗi, dung sai hoặc tính độc lập của test. Chấm đúng/sai vẫn áp dụng từng câu với bản PDF gốc và đúng vùng citation.
