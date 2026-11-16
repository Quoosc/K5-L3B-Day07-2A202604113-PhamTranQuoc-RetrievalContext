# Day 7 — Agentic RAG

**Phạm Trấn Quốc · 2A202604113 · L3B.** Phần cơ bản có đủ bằng chứng cho sáu nhóm rubric tối đa **85 điểm**; test nâng cao v3 đạt **28/30 = 93.33%**, vượt ngưỡng 90% để xét đủ **15 điểm bonus**. Hồ sơ đáp ứng các điều kiện cho mức tối đa **100 điểm** theo tự audit; điểm chính thức do giảng viên quyết định.

[Báo cáo đầy đủ](report/individual/2A202604113_PhamTranQuoc.md) · [Review chốt bài](report/individual/REVIEW_DAY07_2A202604113.md) · [Audit rubric](artifacts/submission-audit.json) · [Runbook](docs/REPRODUCE.md) · [Rubric gốc](RUBRIC.md).

Tác giả đã xác nhận kiểm chứng toàn bộ nguồn tại [biên bản](artifacts/source-verification.json). Không còn bước chờ xác nhận nguồn. Nhãn output ghi đúng vai trò Codex hỗ trợ, có lý do/citation để kiểm lại. Các cờ pending/provisional trong hiện vật lịch sử được giữ nguyên byte và được giải thích bằng [trạng thái hiện hành](benchmarks/advanced-v3/SOURCE_VERIFICATION.md).

## Kết quả đã nộp

| Phần | Kết quả / bằng chứng |
|---|---|
| Cơ bản | Sáu nhóm rubric đủ bằng chứng cho phạm vi 85 điểm. Dense, TF-IDF, RRF cùng corpus Day 6 thật; H1/H2/H3; freeze trước test D0/H0; đủ review/context/citation/lỗi. |
| Nâng cao hiện tại | **V3 A12: 28/30 = 93.33%**, cần 27/30. Dev 78/86; test có 0 lỗi hệ thống và 30 native search thực. |
| Theo nhóm v3 | Bảng 6/6; ảnh 5/5; biểu đồ 5/5; multi-hop 2/4; text 4/4; thiếu evidence 6/6. |
| Lịch sử giữ nguyên | V1 24/30; v2 17/30. Các bộ đã xem trở thành dev v3; test mới đủ 30 câu, không thay riêng câu sai. |
| Kiểm thử | 61/61 unit tests; kiểm source catalog 13/13; checkout nguồn sạch và tái lập có biên bản. |

Hai câu v3 fail là `adv3-test-018` (không chỉ rõ NN/SS) và `adv3-test-020` (retrieval thiếu đoạn SCA, từ chối sai). Giữ nguyên nhãn/trace, không sửa sau test. Phần cơ bản cũng giữ lỗi JSON và trường hợp H0 thấp hơn D0; rubric cơ bản không đặt ngưỡng metric tuyệt đối.

## Chuẩn bị

Cần Python **3.12.10**; dependency pin tại [requirements-lock.txt](requirements-lock.txt). Repo Day 6 cung cấp `src/embeddings.py`, `src/store.py` và E5 `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 chiều. [Manifest/license Day 6](artifacts/base/day6_manifest.json) ghi 8 nguồn CPython 3.12.10, 40 đơn vị RST và 156 chunk B. `page` ở core là đơn vị RST, không phải trang PDF.

Day 6 public tại [repo cá nhân](https://github.com/Quoosc/K5-L3B-DAY06-2A202604113-DataIngestion), pin commit `19a54c590f2c89198225592f2be9b1a926abdffd`. [Runbook](docs/REPRODUCE.md) có lệnh clone/checkout và tải E5; [provenance](artifacts/day6-code-provenance.json) kiểm hai module ngoài repo khớp hash trong freeze.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
$env:PYTHONUTF8 = '1'
$Py = (Resolve-Path '.venv/Scripts/python.exe').Path
$Day6Root = (Resolve-Path '../K5-L3B-DAY06-2A202604113-DataIngestion').Path
$E5Model = Join-Path $Day6Root '.local/model-snapshot'
& $Py -m unittest discover -s tests -v
& $Py -m scripts.validate_submission_benchmarks --output .local/benchmark-validation.json
```

Qwen2.5 7B Instruct Q4_K_M chạy cục bộ qua [llama.cpp b12406 Windows Vulkan](https://github.com/ggml-org/llama.cpp/releases/tag/b12406). Nguồn GGUF là [Ollama qwen2.5:7b](https://ollama.com/library/qwen2.5:7b), SHA-256 `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`; phải kiểm digest vì tag có thể thay đổi. V3 chỉ dùng text model này; vision model/projector chỉ cần cho lịch sử v1/v2.

PDF [USGS Landsat 8 Data Users Handbook v5.0](https://www.usgs.gov/media/files/landsat-8-data-users-handbook) có 114 trang, SHA-256 `baf10fd32ebbc5d21a509869e2879f5ef23f0d275d8bddc01462ed02d18bc756`. Nguồn USGS ghi Public Domain; kiểm riêng quyền hình bên thứ ba. Repo chỉ kèm văn bản/OCR/mô tả nguồn và snapshot tương ứng, không kèm PDF/crop hoặc model weights.

```powershell
New-Item -ItemType Directory -Force .local/downloads | Out-Null
curl.exe -L --fail 'https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/LSDS-1574_L8_Data_Users_Handbook-v5.0.pdf' -o .local/downloads/landsat8-v5.pdf
Get-FileHash -Algorithm SHA256 .local/downloads/landsat8-v5.pdf
```

## Chạy và tái lập

[Runbook](docs/REPRODUCE.md) có toàn bộ lệnh phục hồi index, chạy dev, ghi review, freeze, chạy full test, score và kiểm checkout. Đích output mới, không ghi đè artifact đã nộp. Cần đúng model/PDF/runtime/hash khi dùng lock đã nộp; thay phần cứng hoặc code thì chạy dev/freeze riêng.

Snapshot [core](artifacts/base/qdrant-snapshot.zip) đối chiếu 156/156 payload; [catalog v7](artifacts/advanced/qdrant-v7-snapshot.zip) đối chiếu 941/941 payload. [Thiết kế v3](docs/CATALOG_V3.md) mô tả curation nguồn, retrieval và giới hạn. Runtime không nhận gold. Citation phải đúng nội dung/vùng; ID hợp lệ không tự bảo đảm hỗ trợ câu trả lời.

Tái tổng hợp test v3 đã nộp mà không gọi model:

```powershell
& $Py -m scripts.catalog_release score --split test --traces artifacts/advanced/runs/catalog-v3-test/traces.jsonl --reviews artifacts/advanced/v3-test-review.jsonl --output .local/v3-score.json
& $Py -m scripts.audit_submission --output .local/submission-audit.json
```

Tái lập chính xác lịch sử v2 dùng commit `eec9a4278c5ed1838e3ca3266696f28158db2c51` trong checkout khác; fingerprint v2 quét cả thư mục runtime nên các module v3 mới làm hash tổng tại HEAD khác. Core vẫn khớp freeze gốc. `.gitattributes` bảo toàn byte các đầu vào đã băm, kể cả CRLF có trước.

Không commit `.local`, `.env`, secret, cache hoặc weights. Chi phí API các lượt đo bằng 0 USD; chưa đo điện/khấu hao và thời gian curation. Repo cá nhân public; gửi link theo hướng dẫn lớp khi nộp.
