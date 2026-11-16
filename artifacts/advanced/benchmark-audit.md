# Audit nguồn benchmark nâng cao — bản dự thảo

Nguồn: PDF USGS LSDS-1574 v5.0, SHA-256 trong [manifest](pdf_manifest.json). Validator đã kiểm mọi ID, trang PDF, nhãn in, bbox và số lượng theo nhóm; kết quả cấu trúc **không** tự xác nhận ngữ nghĩa. Các trang sau đã được Codex đọc qua bản render 100 DPI, không tự nhận là human review.

- Trang 13/nhãn 5: bảng 1-1 cho SSR Landsat 7 `378 Gbits, block-based`, Landsat 8 `3.14 Terabit, file-based`, downlink Landsat 8 `X-Band Earth Coverage`; đoạn Global Survey ghi 16 ngày.
- Trang 18/nhãn 10: bảng 2-1 là **ảnh nhúng**, không phải bảng vector mà parser tự hiểu. Hàng Landsat 8 cho các band 1–8 và khoảng bước sóng dùng trong câu multi-hop; phải mở lại đúng hàng khi chấm.
- Trang 19/nhãn 11: bảng 2-2 cho OLI Band 1–9 lần lượt `238, 364, 302, 227, 204, 265, 334, 149, 165`; biểu đồ Figure 2-3 dùng các cột màu và trục SNR. Câu đọc cột có dung sai tuyệt đối 20 vì đọc từ hình.
- Trang 22/nhãn 14: bảng 2-3 cho TIRS 10 tại 240 `0.069`, TIRS 11 tại 280 `0.059`; Figure 2-7 đặt SCA-3 bên trái, SCA-1 bên phải.
- Trang 76/nhãn 68: Table A-1 ghi Band 10 `-2.1 ± 0.8 K @ 300 K`, Band 11 `-4.4 ± 1.75 K @ 300 K`; legend Figure A-3 bên trái cho Band 11 là hình vuông đỏ.
- Các vùng hình ở trang 16, 20, 23, 53, 78, 96 và đồ thị ở trang 58, 75, 79 đã được xem lại theo locator trong gold. Câu hỏi dựa vào nhãn/vị trí/quan hệ trong hình, không chỉ lặp caption. Dung sai đồ thị ở trang 79 là 1 đơn vị theo vạch trục.
- Các câu text ở trang 9, 13, 23, 58, 60, 78 được đối chiếu trực tiếp với đoạn tương ứng. Câu multi-hop bắt buộc nối bảng bước sóng trang 18 với bảng SNR trang 19; hai vùng cần thiết, nhưng nhóm này chỉ dùng hai bảng nên **độ đa dạng nguồn còn hạn chế**.

Dev và test không dùng cùng `fact_keys`, nhưng một số câu trong cùng split tái sử dụng dữ kiện giữa bảng/biểu đồ và multi-hop. Các câu thiếu evidence dùng tên thực thể giả: [audit theo chuỗi v1](absence-audit-v1.summary.json) quét text của 114 trang và OCR chưa kiểm chứng của 77 vùng ảnh/vector, không tìm thấy 12 tên của hai split. Codex đã xem [10 vùng OCR rỗng](empty-ocr-visual-review.md), nhưng OCR có thể bỏ sót, chưa có kiểm tra ngữ nghĩa toàn bộ các hình khác; lý do vắng vẫn là tạm thời. [Đối chiếu từng gold test](benchmark-test-source-review.md) ghi trang và giá trị đã xem, nhưng không phải nhãn kết quả test và chưa có reviewer con người độc lập. Cần người làm đối chiếu từng gold/citation với PDF gốc và hoàn tất audit absence trước khi coi bộ này đủ điều kiện bonus.
