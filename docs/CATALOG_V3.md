# Pipeline nâng cao v3

V3 dùng truy xuất văn bản và dữ liệu có cấu trúc được lập từ toàn bộ PDF, rồi Qwen2.5 7B tạo câu trả lời. Đây là phương án mô tả ảnh/OCR và chuẩn hóa bảng được ADVANCED.md cho phép. V3 không gọi vision model khi trả lời từng câu và không báo số lần xử lý ảnh của những thí nghiệm cũ thành số đo của v3.

## Nguồn và tiền xử lý

[Catalog v6](../artifacts/advanced/catalog-v6/manifest.json) giữ 852 vùng của 114 trang: 744 text, 49 ảnh, 31 bảng ứng viên và 28 trang vector. Mỗi vùng có ID gốc, trang PDF, nhãn in và bbox. Có mô tả cho cả 49 ảnh, bảng theo header/ô nguồn, OCR phụ, toàn bộ hàng phổ của cả Landsat 7 và 8, chú giải/series biểu đồ và lấy mẫu đường Figure A-6 theo 12 mốc ngày. Mô tả được Codex hỗ trợ từ caption/OCR và kiểm hình; không phải lời khẳng định rằng một VLM vừa đọc cả 49 hình ở runtime.

[Catalog v7](../artifacts/advanced/catalog-v7/manifest.json) thêm nhãn Table/Figure của nguồn, tên category đầy đủ cho series SNR, và chia 941 chunk tối đa 450 token, overlap 48. Mô tả và dữ liệu nguồn được xây trước khi tạo benchmark v3; builder không đọc benchmark. Không thêm câu trả lời phủ định cho các thuộc tính được hỏi ở test vào index. Tác giả đã xác nhận toàn bộ nguồn tại [biên bản](../artifacts/source-verification.json).

Một số bảng ứng viên thực chất là đoạn tài liệu tham khảo hoặc có ô gộp khó phân tích. Các ô tự động gốc vẫn được giữ trong `regions.jsonl`, kèm giới hạn; không coi mọi bảng trích tự động đều chính xác. OCR và mô tả có thể sai; tọa độ gốc và bản PDF là căn cứ khi chấm. Số vùng được index không tự chứng minh mọi câu hỏi về tài liệu đều trả lời được.

## Agent và giới hạn

Qwen2.5 7B chọn native `search`. Retriever kết hợp query gốc và query viết lại qua E5/Qdrant + TF-IDF/RRF. Nếu câu hỏi nêu Table/Figure thì tra nhãn trong inventory nguồn; nếu nêu section thì dùng heading thực tế. Không dùng ID gold để định tuyến. Tối đa ba vùng, mỗi vùng 10.000 ký tự, tổng context 6.000 token. Các hàng khớp cụm từ của câu hỏi được sao chép từ bảng nguồn để giảm đọc nhầm cột.

Ngân sách là một lần thực thi search. Nếu model đề xuất nhiều tool call, chỉ thực thi đề xuất hợp lệ đầu tiên, ghi rõ các đề xuất còn lại không chạy. Nếu không có đề xuất hợp lệ, controller ghi `controller_protocol_recovery` rồi thực sự tìm bằng câu hỏi gốc. Trace của nhánh này ghi `native_call_executed: false`; không giả lập một native tool call thành công. Timeout/lỗi model vẫn là `error`, không đổi thành abstain.

Model cuối nhận lại nguyên câu hỏi để giữ đủ hai phía của so sánh hoặc phép tính. Output chỉ có `answer` và `citations`; sentinel `INSUFFICIENT_EVIDENCE` là từ chối do model khai báo. Renderer gắn đúng alias đã khai báo, không tự sửa dữ kiện hay biến lời từ chối thành câu trả lời. ID citation hợp lệ vẫn phải qua review hỗ trợ ngữ nghĩa.

## Quy trình đo

V1 đạt 24/30, v2 đạt 17/30; cả hai được giữ làm lịch sử. Toàn bộ 86 câu đã xem chuyển sang dev v3. 30 câu test v3 dùng thuộc tính/quan hệ mới, đúng quota 6 bảng, 5 ảnh, 5 biểu đồ, 4 multi-hop, 4 text, 6 thiếu evidence. Sáu câu thiếu hỏi thuộc tính không được cung cấp của thực thể thật.

Chỉ freeze sau khi review đủ 86 câu dev và đạt ít nhất 78/86. Lock băm code, catalog, toàn bộ benchmark, model, PDF, E5 và DB; runtime attestation kiểm executable/command line thực tế. Test phải chạy đủ 30 câu, không có cờ giới hạn, không thay riêng câu sai. Sau test, giữ cả lỗi/từ chối sai và đối chiếu từng citation với bản gốc; cần ít nhất 27/30. Scorer chỉ tổng hợp các nhãn gắn với SHA của đúng trace, không phải judge tự động.

Lệnh tái lập đầy đủ nằm trong [runbook](REPRODUCE.md). Tái lập chính xác v2 dùng checkpoint `eec9a4278c5ed1838e3ca3266696f28158db2c51`; v2 băm toàn bộ thư mục runtime nên các module v3 bổ sung sẽ làm hash của root hiện tại khác lock v2. Phần cơ bản băm danh sách module cố định và vẫn giữ nguyên byte.
