# Kiểm tra trực quan mẫu tài liệu Landsat 8 v5.0

Ngày kiểm tra: 15/11/2026; công cụ: Poppler 26.09.0 render 100 DPI và PyMuPDF 1.26.7. Đây là kiểm tra của Codex, không phải xác nhận của người chấm. PDF gốc: [USGS](https://www.usgs.gov/media/files/landsat-8-data-users-handbook), SHA-256 `baf10fd32ebbc5d21a509869e2879f5ef23f0d275d8bddc01462ed02d18bc756`. Ảnh render dùng để kiểm tra cục bộ, không đưa vào repo.

| Trang PDF / nhãn in | Nội dung quan sát | Kết quả trích xuất và giới hạn |
|---|---|---|
| 9 / 1 | Text mở đầu và ảnh phóng vệ tinh. | Text trích được; `landsat-v5-p009-image-001` bao ảnh, nhưng không có mô tả ảnh. |
| 13 / 5 | Bảng 1-1 so sánh Landsat 7 và 8; dòng Scenes/Day khoảng 450 và 700. | `landsat-v5-p013-table_candidate-001` bao bảng và giữ hai giá trị; parser sinh nhiều cột rỗng do ô gộp, nên không được mặc định coi mọi cột đã đúng. |
| 16 / 8 | Hình 2-1 có nhãn TIRS, OLI, spacecraft bus và solar panel. | `landsat-v5-p016-image-001` bao hình và lấy caption; các nhãn nằm trong ảnh, không có trong mô tả đã index. |
| 19 / 11 | Bảng 2-2 và biểu đồ cột Figure 2-3, có trục SNR, band và ba nhóm trong chú giải. | `landsat-v5-p019-image-001` bao biểu đồ; `landsat-v5-p019-table_candidate-001` bao bảng nhưng header nhiều tầng bị tách thành nhiều cột rỗng. Caption không đủ để đọc đồ thị. |

Inventory và các vùng là **ứng viên trích xuất**, chưa phải kiểm chứng rằng toàn bộ nội dung hữu ích, nhất là chữ/quan hệ trong hình và biểu đồ, đã được hiểu hoặc truy xuất chính xác. Chưa có căn cứ tính 15 điểm nâng cao. Với từng vùng được dùng để chấm cần mở lại đúng bbox trong PDF gốc; không dùng mô tả tự sinh làm gold.

Một probe ngoài benchmark với truy vấn `Illustration of Landsat 8 Observatory Figure 2-1` đưa `landsat-v5-p016-image-001` lên hạng 1 trong hybrid; lệnh `render-region` mở đúng hình Figure 2-1 ở trang PDF 16. Xem [trace tìm kiếm](search-smoke.json). Đây chỉ là tìm bằng caption và mở vùng, chưa chứng minh model đọc được nhãn trong ảnh.
