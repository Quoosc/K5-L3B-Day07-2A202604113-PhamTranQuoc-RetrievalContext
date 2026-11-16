# Đối chiếu nguồn của benchmark test nâng cao

Đây là kiểm tra gold trước khi chạy test, **không phải kết quả agent**. Codex đã xem ảnh render của PDF gốc và đối chiếu các locator đã ghi trong `benchmarks/advanced/gold/test.jsonl`. Số trang bên dưới là số trang PDF; không tự nhận có reviewer con người độc lập. Cần xem lại bbox trên PDF gốc khi chấm từng câu test.

| ID | Trang PDF | Quan sát từ nguồn |
|---|---:|---|
| 001 | 13 | Table 1-1, SSR Landsat 8: 3.14 Terabit, file-based. |
| 002 | 19 | Table 2-2, OLI Band 7, OLI Performance: 334. |
| 003 | 22 | Table 2-3, TIRS 11, NEΔT@280: 0.059. |
| 004 | 76 | Table A-1, Band 11, temperature offset: -4.4 ± 1.75 K tại 300 K. |
| 005 | 18 | Table 2-1, Landsat 8 Band 5: 0.851–0.879 µm. |
| 006 | 13 | Table 1-1, Image D/L Landsat 8: X-Band Earth Coverage. |
| 007 | 16 | Figure 2-1 ghi Solar Panel ở phía dưới bên phải spacecraft bus. |
| 008 | 20 | Đầu cột Even SCAs ở Figure 2-5 là 12–14 Blind. |
| 009 | 23 | Figure 2-8 cho hai baffle gắn với phía Nadir bên trái và Spaceview Calibration bên phải; đây là suy luận từ vị trí và các mũi tên. |
| 010 | 78 | Figure A-5 ghi Focal Plane Array (FPA) ở đáy hình cắt. |
| 011 | 96 | Figure B-2 đặt SCA-C/SCA02 dưới hàng SCA-A và SCA-B. |
| 012 | 19 | Figure 2-3: cột đỏ NIR gần 204; dung sai tuyệt đối 20. |
| 013 | 19 | Figure 2-3: cột đỏ Cirrus gần 165; dung sai tuyệt đối 20. |
| 014 | 79 | Figure A-6: đường giới hạn đỏ ở khoảng 85; dung sai tuyệt đối 1. |
| 015 | 58 | Figure 4-3: hai band TIRS ở phía bước sóng nhiệt là 10 và 11. |
| 016 | 76 | Legend panel trái Figure A-3 dùng hình vuông đỏ cho Band 11. |
| 017 | 18, 19 | Table 2-1: 0.851–0.879 µm là Band 5; Table 2-2: OLI Performance 204. |
| 018 | 18, 19 | Table 2-1: 1.566–1.651 µm là Band 6; Table 2-2: OLI Performance 265. |
| 019 | 18, 19 | Table 2-1: 2.107–2.294 µm là Band 7; Table 2-2: OLI Performance 334. |
| 020 | 18, 19 | Table 2-1: 0.503–0.676 µm là Band 8; Table 2-2: OLI Performance 149. |
| 021 | 13 | Mục Global Survey Mission nói toàn thế giới đi vào tầm nhìn một lần mỗi 16 ngày. |
| 022 | 58 | Mục dynamic range nêu 4.096 mức xám cho 12 bit và 256 cho 8 bit. |
| 023 | 60 | Mục QA cho biết pixel nhiễm mây làm giảm NDVI và có thể làm sai đo phenology. |
| 024 | 78 | Appendix A.2 nêu lần đầu phát hiện ngày 19 tháng 12 năm 2014. |

Các ID 025–030 là câu thiếu evidence với thực thể giả. [Audit v1](absence-audit-v1.summary.json) không thấy 12 tên thực thể của cả dev/test trong text trích xuất của 114 trang hoặc OCR của 77 vùng ảnh/vector. Phép tìm chuỗi và OCR có thể bỏ sót, trong đó 10 vùng không có chữ OCR; chúng **không** chứng minh vắng thông tin trong mọi hình. Các tên giả và câu multi-hop cùng hai bảng cũng làm độ đa dạng benchmark còn hạn chế.
