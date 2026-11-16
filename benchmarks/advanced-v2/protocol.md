# Protocol cho holdout nâng cao thứ hai

Test đầu tiên đã được xem và đạt 24/30. Mọi cải tiến dựa vào lỗi đó coi cả test cũ là dữ liệu phát triển; không được báo lại test cũ như đánh giá độc lập của pipeline mới. Bộ mới chỉ được chạy sau khi benchmark, pipeline, model, nguồn, chỉ mục và tiêu chí chấm đã khóa trước.

- Giữ một tài liệu Landsat 8 v5.0 và tách query/gold; model và tool không nhận gold.
- Test mới có 30 câu: 6 bảng, 5 ảnh/sơ đồ, 5 biểu đồ, 4 multi-hop, 4 text và 6 thiếu evidence. Mỗi câu có một nhóm chính.
- Câu có đáp án phải dùng dữ kiện và đáp án khác với dev/test cũ; không chỉ đổi cách hỏi. Ưu tiên vùng nguồn mới, trải trên ít nhất 10 trang PDF và nhiều mục. Bốn câu multi-hop phải dùng ít nhất hai cặp nguồn khác nhau.
- Ít nhất ba câu thiếu evidence hỏi thuộc tính cụ thể của thực thể có thật; nếu dùng thực thể giả cho các câu còn lại, ghi rõ đây là phép thử dễ. Đối chiếu text, OCR và vùng liên quan; không suy luận vắng toàn corpus từ top-k.
- Lập đáp án, trang, bbox, điều kiện/đơn vị, phép tính và dung sai trước khi chạy bất kỳ pipeline nào trên test mới. Mọi đáp án phải được đối chiếu PDF gốc; nhãn ghi đúng người thực hiện và nguồn hỗ trợ. Tác giả đã xác nhận kiểm chứng toàn bộ nguồn tại `artifacts/source-verification.json`; nhãn đầu ra do Codex hỗ trợ được ghi riêng, không tự nhận là nhãn do một người chấm bên ngoài tạo.
- Không chọn hoặc thay câu dựa trên output model. Nếu thấy lỗi benchmark trước khi chạy thì lưu lý do và khóa lại; nếu đã chạy và dùng kết quả để thay đổi cấu hình hoặc câu hỏi thì phải tạo holdout khác.
- Chấm cả 30 câu và mọi lỗi, timeout, từ chối, citation không hỗ trợ. Ngưỡng 90% nghĩa là ít nhất 27/30, không làm tròn; yêu cầu index/source/audit vẫn áp dụng.

Trạng thái thiết kế: **benchmark đã được tạo trước chạy model**: dev 56 câu từ v1, test mới 30 câu trên 23 trang; đủ quota, bốn cặp nguồn multi-hop và sáu câu thiếu thuộc tính của thực thể thật. Một locator của câu 023 được sửa từ đoạn bảng sang đoạn CPF đúng trước khi chạy bất kỳ model nào trên test mới; lịch sử sửa nằm trong manifest. Kết quả chính thức chỉ có giá trị sau freeze và chạy đủ test; xem báo cáo bài nộp để biết trạng thái cuối cùng.
