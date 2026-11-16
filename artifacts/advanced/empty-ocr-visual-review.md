# Kiểm tra trực quan các vùng OCR không nhận chữ

Codex đã mở 10 crop từ PDF gốc tại 110 DPI. Những nhận xét dưới đây chỉ mô tả hình nhìn thấy, không suy đoán ý nghĩa khoa học hoặc nội dung ngoài crop. Đây không phải review độc lập của con người; chúng không có trong index v4 đã dùng cho thí nghiệm, nhưng đã được bổ sung có gắn nhãn AI vào [index v5](search-manifest-v5-supplement.json). Bbox và mã nguồn nằm trong `elements.jsonl`.

| Vùng | Quan sát trực quan |
|---|---|
| `landsat-v5-p009-image-001` | Ảnh tên lửa đang phóng bên cạnh giàn phóng. |
| `landsat-v5-p044-image-001` | Ảnh xám tối có một vệt sáng hẹp gần thẳng đứng. |
| `landsat-v5-p061-image-001` | Ảnh xám dạng hình chữ nhật nghiêng trên nền đen, có nhiều vùng sáng tối. |
| `landsat-v5-p083-image-001` | Hai ảnh đặt cạnh nhau; ảnh trái có màu, ảnh phải sáng/xám, mỗi ảnh có khung đỏ. |
| `landsat-v5-p088-image-001` | Ảnh xám có nhiều vệt tối mảnh chạy chéo. |
| `landsat-v5-p089-image-001` | Ảnh xám có nhiều dải sáng tối gần thẳng đứng. |
| `landsat-v5-p090-image-001` | Ảnh xám có vùng sáng và tối không đều, kèm các dải mờ. |
| `landsat-v5-p091-image-001` | Ảnh xám tương phản mạnh với một hình chữ nhật và mũi tên đỏ. |
| `landsat-v5-p092-image-001` | Ảnh xám có kết cấu hạt và các đường sáng cong/chéo. |
| `landsat-v5-p094-image-001` | Ảnh xám tối có hai cụm chấm sáng. |

Không thấy tên giả của benchmark trong các crop này ở độ phân giải đã xem. Việc này không xác minh nội dung của 67 vùng OCR còn lại, không loại trừ chữ nhỏ/OCR sai, và không chứng minh vắng mọi thông tin có liên quan trong tài liệu.
