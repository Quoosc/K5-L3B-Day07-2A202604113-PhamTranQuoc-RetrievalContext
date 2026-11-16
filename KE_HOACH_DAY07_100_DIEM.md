# Kế hoạch Day 7 — Agentic RAG | mục tiêu 100/100

**Phạm Trấn Quốc · 2A202604113 · L3B**  
Repo rà soát: `E:\VINAITHUCCHIEN\K5-L3B-Day07-PhamTranQuoc-2A202604113-RetrievalContext`  
Mốc đối chiếu: `main` · `c67ec6292cd6d15e6e6cbaa2c7e7260398bb5a19` · 15/11/2026

Để nhắm **100/100**, cần đủ **85 điểm cơ bản** và đủ điều kiện nhận **15 điểm nâng cao**. Phần cơ bản được chấm theo chất lượng triển khai, thiết kế thí nghiệm và bằng chứng, không có ngưỡng metric bắt buộc. Phần nâng cao chấm trọn 15 hoặc 0: phải hoàn thành toàn bộ yêu cầu và đạt **ít nhất 27/30** nếu chốt test đúng 30 câu. File này là kế hoạch và biên bản rà soát, chưa phải kết quả làm lab hay điểm đã được xác nhận.

## 1. Review repo hiện tại

Đã rà 30 file ngoài `.git` trong thư mục làm việc, gồm hướng dẫn, rubric, benchmark cơ bản và nâng cao, hướng dẫn nộp, 4 module starter, 4 file test, fixture, sơ đồ và mẫu báo cáo. Đã kiểm tra đường tích hợp với repo Day 6 liền kề.

| Phát hiện | Tác động | Việc phải làm |
|---|---|---|
| `src/README.md` mới chỉ giữ chỗ. `starter/agentic.py:10–28` chỉ có protocol `Controller` và `Retriever`; `tests/test_agentic.py` dùng adapter giả. | Chưa có agent thật, dense Day 6 hoặc đo benchmark thật. | Dùng launcher/runner mới và kết nối provider thật, ghi trace theo từng câu. |
| `starter/baseline.py` chỉ có TF-IDF, không áp filter; yêu cầu mọi câu có `expected_answer` và `gold` (`:40–54`). Hit dùng đúng nguồn/trang và quote nằm trọn trong một chunk. | Không nạp được benchmark hỗn hợp có câu thiếu bằng chứng; cách chấm mẫu không kiểm đủ bằng chứng multi-hop. | Viết validator/evaluator tách khỏi runtime; giữ fixture để smoke test và mở rộng schema theo §4. |
| `starter/convert_day6.py:7–24` đổi trường nhưng CLI chỉ đọc JSON array; không mang `alternatives` hoặc offset qua cấu trúc đích, không tự kết nối Qdrant. | Day 6 thực tế dùng JSONL; chuyển nguyên xi có thể bỏ nguồn tương đương và thông tin định vị. | Viết adapter JSONL/payload Qdrant, bảo toàn ID, offset và metadata; kiểm chứng riêng bộ câu hỏi trước khi dùng. |
| `starter/agentic.py:57–72` pack lại theo thứ tự đến; `pack_context` mặc định 800 ký tự và bỏ cả đoạn không vừa. Citation được kiểm tra ID/list và sự xuất hiện trong câu trả lời. | Đoạn tìm trước có thể chặn evidence tìm sau; citation đúng ID vẫn có thể sai nội dung. Khung cũng chưa kiểm mọi marker citation trong prose. | So sánh packer theo token và độ phủ; dùng abstain rõ ràng, kiểm marker, chấm từng mệnh đề bằng nguồn thật. |
| `starter/agent_metrics.py:24–65` tổng hợp nhãn tay; bỏ `status:error` khỏi các mẫu số chất lượng; không tổng hợp phân bố lượt gọi và điểm context. | Có thể dùng làm điểm khởi đầu cho phần cơ bản, nhưng không được dùng mẫu số này để xét bonus. | Bổ sung coverage, lỗi theo split/nhóm, phân bố lượt gọi, chấm context; dùng scorer nhị phân riêng cho nâng cao. |
| Fixture chỉ có 1 chunk, 1 câu retrieval dev; `agent_cases_example.json` chỉ minh họa 2 câu. `report/individual/` chỉ có mẫu. | Chưa có câu hỏi thật, split được chốt, trace hay hồ sơ nộp. | Tạo 2 benchmark độc lập, báo cáo `report/individual/2A202604113_PhamTranQuoc.md` và bộ hiện vật có thể tải/chạy lại. |
| `.gitignore` bỏ qua `starter/data/` và `starter/results/`. | Trace và nhãn lưu trong các thư mục này có thể thiếu trong bài nộp. | Lưu hiện vật được phép chia sẻ trong `artifacts/` và kiểm bằng `git ls-files`. |
| Python 3.11.9 trên Windows: chạy trên bản sao, mặc định **14 pass, 1 lỗi** `UnicodeDecodeError` tại `tests/test_baseline.py:73`; bật `PYTHONUTF8=1` thì **15/15 pass**. Smoke TF-IDF trên fixture: `Hit@1`, `Hit@3`, context hit đều `1/1`. | Lỗi do test đọc file UTF-8 bằng encoding mặc định của Windows. Fixture pass chỉ chứng minh starter chạy. | Khi triển khai, thêm `encoding="utf-8"` cho các chỗ đọc JSON trong test; chạy lại cả lệnh mặc định và lệnh README. |
| Probe thật Day 6 bằng venv Python 3.12.10, model snapshot trên máy và DB sao chép: `lab6_B` có **156 điểm**, vector **384 chiều**, norm xấp xỉ 1; truy vấn thử về đọc JSON trả đủ 3 payload có nguồn/trang/score, đứng đầu `library-json`, đơn vị 1. | Đã xác minh đường tích hợp model embedding và vector store có thể chạy; đây chưa phải kết quả agent hoặc benchmark Day 7. | Dùng lại đúng snapshot/collection; vẫn cần adapter Day 7, đối chiếu toàn bộ ID và gọi model sinh thật. |

`BENCHMARK.md` và `ADVANCED.md` là căn cứ cho cách chia tập, chạy thí nghiệm và chấm điểm trong kế hoạch này. `AGENT_SETUP.md` là tài liệu tùy chọn. Lịch 4 giờ trong `CHECKPOINTS.md` dành cho phần cơ bản.

## 2. Ma trận nghiệm thu theo rubric

| Tiêu chí gốc | Điểm | Hiện vật cần có để người chấm kiểm được |
|---|---:|---|
| Dữ liệu và benchmark | **13 = 6 + 7** | 6: manifest Day 6, cấu hình E5/Qdrant, kiểm đếm/tương thích và nguồn. 7: case, gold evidence, lý do vắng dữ liệu, split và hash, audit nguồn/trang. |
| Retrieval | **17 = 10 + 7** | 10: dense trên Qdrant Day 6, lexical, hybrid, mỗi phương pháp có code và chạy cùng dev. 7: cấu hình, filter, top-3/rank/score/nguồn, tie-break và lỗi thực tế. |
| Agent và context | **17 = 9 + 8** | 9: một model thật điều phối tool, trace và lý do dừng. 8: context thực gửi, quyết định giữ/bỏ evidence, citation truy ngược được và abstain có căn cứ. |
| Đánh giá | **17 = 9 + 8** | 9: Hit@1, Evidence Hit@3, Context Evidence Rate, đánh giá context test `0/1/2`, cùng mẫu số. 8: nhãn grounded answer, audit citation, abstention, tool use và lỗi. |
| Thử nghiệm và cải thiện | **13 = 5 + 5 + 3** | 5: ít nhất 2 cấu hình cải thiện riêng, tối thiểu 2 lỗi dev có phân tích trước/sau. 5: tiêu chí công bố trước, freeze trên dev, baseline và cấu hình chọn chạy cùng test. 3: so sánh chất lượng, độ trễ, token và chi phí. |
| Tái lập và báo cáo | **8 = 5 + 3** | 5: code, dependency, lệnh, phiên bản model, index và dữ liệu/quyền truy cập. 3: kết luận theo số đo, nguồn, giới hạn và báo cáo đúng tên. |
| **Tổng cơ bản** | **85** | Đủ sáu dòng trên, kể cả khi một thử nghiệm cho kết quả kém hơn baseline. |
| Nâng cao | **15 hoặc 0** | Một PDF thực tế ≥100 trang; toàn bộ nội dung hữu ích được lập chỉ mục hoặc ghi rõ ngoại lệ; split riêng, nhãn cho từng câu test và đủ bằng chứng tái lập. Tỷ lệ test ≥90%, gồm cả lỗi/timeout trong mẫu số. |
| **Tổng mục tiêu** | **100** | Chỉ ghi hoàn tất khi tự audit đủ 85 điểm cơ bản và đạt toàn bộ điều kiện bonus. |

## 3. Mốc 1 — nối Day 6 và dựng môi trường chạy

Day 6 cá nhân nằm tại `E:\VINAITHUCCHIEN\K5-L3B-DAY06-2A202604113-DataIngestion`. `artifacts/selection.json` xác nhận cấu hình **B** được chọn trên dev. `results/chunks/B.jsonl` có **156 chunk**; `data/normalized/pages.jsonl` có **40 đơn vị RST chuẩn hóa từ 8 nguồn CPython 3.12.10**. `page` là số đơn vị trong nguồn RST, không phải trang PDF. Bản local có `.local/qdrant/collection/lab6_B`, `.local/model-snapshot` và venv Python 3.12.10. `results/run_manifest.json` khai báo E5 `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, **384 chiều**, CPU, cosine exact search, chuẩn hóa vector, prefix `query: ` và `passage: `. 

1. Dùng Python 3.12.10 để khớp môi trường Day 6 nếu có. Pin dependency Day 7 và ghi phiên bản Day 6 từ `requirements-lock.txt`/manifest. Cấu hình đường dẫn `DAY6_ROOT`, Qdrant, model snapshot, model sinh và cache qua file mẫu/env; không nhúng đường dẫn `E:\...` trong code dùng để nộp. Lấy model sinh thật có tool calling và, ở nhánh nâng cao, hỗ trợ ảnh hoặc có một adapter vision riêng. Sau khi chọn, ghi model ID, phiên bản, chế độ local/API, giới hạn và cách tính giá; chỉ chuyển tài liệu sang API nếu được phép.
2. Đọc `data/manifest.json`, license CPython, `artifacts/model_download.json` và `artifacts/config_freeze.json`; ghi checksum corpus, chunk B, manifest model và thông số collection vào `artifacts/base/day6_manifest.json`. Mở bản sao Qdrant khi DB gốc không có writer, hoặc chạy ingest Day 6 vào thư mục tái lập riêng theo README Day 6. Không chạy lại test Day 6 để tạo số liệu Day 7. Dùng code tương thích API `LocalEmbedder.embed_query()` và `QdrantStore.search("lab6_B", ...)`; không thêm prefix hai lần. Export cùng payload/chunk B cho lexical và hybrid, đối chiếu tập ID giữa hai nguồn. Dùng `chunk_id` gốc, không dùng UUID nội bộ của Qdrant làm citation.
3. Adapter Day 7 ánh xạ `chunk_id → id`, `document_id → source_id`, giữ `source`, `page`, `metadata`, `start_offset`, `end_offset`, `token_count`; thêm `rank`, `score`, `method` lúc truy xuất. Tạo nhãn nguồn hiển thị `doc_id · đơn vị RST N · offset X–Y` với URL snapshot. Kiểm filter whitelist (`section`, `document_type`, `language`, `version`), filter rỗng, lỗi DB, dimension và score hữu hạn. Filter chỉ nhận scope được user đưa hoặc suy ra từ query theo quy tắc công bố; ưu tiên một chính sách giống nhau ở ba phương pháp khi so sánh.
4. Smoke test model sinh gọi tool trên câu ngoài holdout. Kiểm ledger: search có query thật, top-3 có nguồn và score/rank, trả citation đúng chỗ; thử một câu thiếu bằng chứng, một lỗi DB/model và một tài liệu chứa câu lệnh giả để xác nhận nội dung truy xuất chỉ là dữ liệu.

**Qua mốc:** đo thực tế vector 384 chiều, collection có 156 ID khớp export B, truy vấn thật trả payload đúng, model thật gọi tool; ghi lệnh và kết quả probe. Nếu mất model/DB, tạo lại từ bản Day 6 đã pin, không dùng vector ngẫu nhiên hoặc fixture thay corpus.

## 4. Mốc 2 — chuẩn bị benchmark và khóa holdout

| Bộ | Dev đề xuất | Test đề xuất | Điều kiện và xuất xứ |
|---|---:|---:|---|
| Cơ bản | **20 có + 3 thiếu = 23** | **5 có + 2 thiếu = 7** | Vượt tối thiểu 15+2 ở dev; đủ 5+2 test. Chỉ dùng lại câu Day 6 **dev** khi kiểm lại với corpus B, có thể thay bằng câu mới trước khi khóa. Test Day 7 viết mới và không lặp cùng sự kiện/đáp án với dev hoặc test Day 6 đã dùng để đo. |
| Nâng cao | **20 có + 6 thiếu = 26** | **24 có + 6 thiếu = 30** | Dev tối thiểu 15+3, bao phủ 5 nhóm. Phân bổ test bắt buộc ở §7. Tách khỏi CPython, cùng một bản PDF đã chốt cho cả dev/test của thử thách. |

- Soạn câu hỏi dựa trên nguồn gốc; có câu hỏi trực tiếp, diễn đạt lại, điều kiện hoặc dễ nhầm phiên bản. Day 6 có 20 dev và 10 test answerable; `alternatives` là trường riêng và báo cáo Day 6 ghi nhận đính chính bằng chứng tương đương, nên đối chiếu với `benchmark/human_review.json` và corpus thay vì giả định mọi quote trong file cũ đều đủ. Giữ câu nếu nguồn, trang/đơn vị, điều kiện và đoạn chứng minh khớp; đề xuất đủ nhóm kèm ID truy vết.
- Schema case: `id`, `split`, `question`, `answerable`, `primary_group` (nâng cao), `expected_answer` hoặc `expected_behavior`, `evidence_groups`, `absence_reason`, `review_reason`. Một nhóm evidence là tập vị trí thay thế (OR); các nhóm bắt buộc phải hiện diện đủ (AND). Evidence cơ bản gồm snapshot/source, đơn vị, ID chunk hoặc offset/quote; evidence PDF thêm `pdf_page`, `printed_label`, `bbox`, loại, ô/hàng/cột hoặc nhãn hình, đơn vị và dung sai/phép tính nếu dùng. Thống nhất cách xác nhận bằng chứng tương đương trước khi đo.
- Câu thiếu evidence: gần chủ đề và có lý do xác định được. Tra mục lục, từ đồng nghĩa, tên thực thể, đơn vị, khoảng thời gian và các trang/nguồn liên quan; lưu ghi chú phạm vi đã rà. Top-k không có kết quả không chứng minh tài liệu thiếu thông tin. Không đưa `answerable`, nhóm, gold, evidence ID/vùng, đáp án, lý do vắng dữ liệu hoặc filter suy ra từ gold vào agent.
- Tách `queries/dev.jsonl`, `queries/test.jsonl` chứa câu hỏi và scope user cho phép khỏi `gold/dev.jsonl`, `gold/test.jsonl`. Runtime chỉ đọc câu hỏi/scope; scorer mới ghép trace với gold theo `query_id`. Có thể giữ test/gold riêng đến lúc freeze, sau đó đóng gói để người chấm kiểm. Lưu số câu theo nhóm, phép so trùng câu và trùng sự kiện, timestamp, SHA‑256 và người review trước dev. Chuẩn bị test trước không đồng nghĩa được dùng kết quả test để chỉnh pipeline.

**Qua mốc:** validator kiểm số lượng, ID, loại câu, phạm vi filter, định vị gold, các lựa chọn thay thế và đủ nhóm multi-hop; người làm kiểm nguồn và chốt benchmark. Khi chạy dev, lệnh benchmark không đọc truy vấn hoặc gold test. Nếu thay test vì nhiễm, có file mới, hash mới và ghi rõ lý do.

## 5. Mốc 3 — ba phương pháp, agent thật và hai cải tiến

Chạy retrieval trên cùng snapshot B với **query gốc** trước. Tiếp theo chạy agent thật trên cùng dev cho từng cấu hình. Dùng cùng model/prompt, giới hạn và chính sách filter khi mục đích là so ba phương pháp; nếu agent viết lại query hoặc tìm nhiều lượt, giữ trace và báo kết quả pipeline dưới cột riêng. Chọn top-3 cố định cho bảng so sánh dù ứng dụng lấy nhiều ứng viên hơn. Các giá trị dưới đây là cấu hình khởi đầu được đề xuất; chốt tiêu chí và điều kiện đo trước khi chạy, ghi lại mọi thay đổi trên dev.

| ID | Phương pháp / cấu hình | So với | Giả thuyết và cách kiểm |
|---|---|---|---|
| D0 | Dense E5 + `lab6_B`, cosine exact; lấy 3; tối đa 1 lượt tool; pack theo rank trong 1.200 token | Baseline chính, chạy cả dev và test sau freeze | Bám ngữ nghĩa và là mốc so chất lượng/chi phí. |
| L0 | Lexical TF-IDF; chuẩn hóa NFC/case; cân nhắc giữ định danh như `json.loads`, ghi tokenizer; lấy 3 | D0, giữ phần agent và packer | Query chứa tên hàm/thuật ngữ cụ thể có thể tìm chính xác hơn. |
| H0 | Hybrid: RRF trên thứ hạng dense và lexical; mỗi nhánh lấy 10 ứng viên, hợp nhất rồi lấy 3; `RRF(d) = Σ 1/(60 + rank)` ở các nhánh có `d`, tie theo ID | D0 và L0 | Kết hợp tên chính xác với diễn đạt lại; lưu rank từng nhánh và điểm RRF. Chi phí pool 10 là một phần của phương pháp, phải báo. |
| H1 | H0 giữ pool nhánh, tăng tập cấp cho packer từ 3 lên 6, giữ budget và số lượt; log cả 3 kết quả đầu | H0 | Evidence xếp hạng thấp bị cắt trước khi pack; đo Context Evidence Rate, grounding, token và câu suy giảm. |
| H2 | H0 giữ lượt, top-k, budget; đổi packer: bỏ đoạn trùng, ưu tiên độ phủ câu hỏi và giữ header/điều kiện khi trích; lấy lại vùng lân cận nếu đã đăng ký trong chính sách | H0 | Giảm đoạn lặp hoặc thiếu điều kiện; đo evidence còn lại trong context và mức chấm tay. |
| H3 (nếu dev cho thấy cần) | Cho thêm một lượt tìm có lý do hoặc rerank pool, thử riêng từng thay đổi; giữ ranking query gốc làm mốc | H0 hoặc biến thể đã ghi rõ | Gỡ lỗi evidence rải ở nhiều đoạn; đo chênh lệch với lượt gọi, p95 và chi phí. |

So sánh tối thiểu D0, L0, H0 và hai cải tiến độc lập H1, H2. Có thể thay H1/H2 bằng thử nghiệm khác nếu lỗi dev chỉ ra nguyên nhân khác, nhưng phải giữ kết quả gốc và ghi bộ đối chứng. Không cộng score cosine và lexical trực tiếp. Với từng lượt, ghi `method`, `rank`, `score`, nguồn, filter, count, latency và candidate được giữ/bỏ. Phân biệt không tìm thấy evidence với timeout, lỗi model/DB, cấu hình sai hoặc retry cạn. Nếu có retry, cố định trước số lần, đo đủ số lần thử và tổng chi phí.

Thiết kế agent nhỏ, có thể dùng một tool `search(query, scope)` gắn backend theo cấu hình. Model thật quyết định tìm và nội dung query; ở cấu hình nhiều lượt, model quyết định khi nào cần tìm tiếp. Schema tham số được xác thực; backend chỉ truy vấn corpus đã chỉ định. Sau mỗi lượt, agent nhận evidence có ID và nguồn. Đặt giới hạn lượt, token, timeout và phát hiện query lặp. Khi hết lượt nhưng đã đủ evidence, gọi bước kết luận chỉ cho phép trả lời hoặc abstain; ghi `stop_reason`. Lỗi hệ thống có trạng thái `error`, không giả làm abstain đúng. Lưu cả trace từng lượt và **context cuối thực sự gửi model**, kể cả crop nếu có. Tính budget sau khi thêm tiêu đề, nguồn, prompt và token ảnh; ghi bộ đếm thực tế hoặc cách ước lượng.

Đầu ra có `status`, `answer`, `citations`, `stop_reason`. Chỉ nhận citation trỏ tới evidence trong context thực gửi; danh sách ID và marker trong câu trả lời khớp nhau. Render link nguồn theo registry, không lấy trang/vùng model tự đoán. Có thể gắn citation ở từng điều kiện, giá trị và phép tính. Nếu thiếu một phần bắt buộc, cho phép một lượt tìm tiếp trong giới hạn hoặc trả lời rõ không đủ bằng chứng, không điền phần thiếu bằng kiến thức ngoài. Điểm semantic do người review đối chiếu bản gốc.

**Qua mốc:** có bảng kết quả riêng cho ba phương pháp và hai cải tiến, các config chạy được, real tool call truy vết được; test phần mềm bao phủ filter, lỗi kết nối, ID sai, prune thiếu điều kiện, nhiều lượt, và dữ liệu truy xuất không được thực thi như chỉ dẫn.

## 6. Mốc 4 — đo, phân tích dev, khóa cấu hình rồi mới chạy test cơ bản

| Chỉ số | Quy tắc và mẫu số |
|---|---|
| **Hit@1 / Evidence Hit@3** | Số câu có đáp án có ít nhất một evidence hợp lệ trong top-1/top-3 chia tổng câu có đáp án. Cố định cutoff, dùng quy tắc khớp nguồn/trang/vùng và nội dung; baseline với ranking có lỗi giữ case trong tổng và log lỗi. Nếu multi-hop, báo riêng tỷ lệ có đủ tất cả nhóm evidence trong top-k để tránh hiểu hit đơn lẻ là đủ. |
| **Context Evidence Rate** | Số câu có **đủ** nhóm evidence hợp lệ trong context cuối thực gửi chia tổng câu có đáp án. Chấm trên nội dung thật sau khi cắt, không chỉ nhìn danh sách ID. Báo budget, đơn vị, số ứng viên, cách pack và độ phủ. |
| **Chấm context** | Từng câu test có đáp án, cho **cả baseline và cấu hình chọn** (ít nhất 5 câu mỗi cấu hình): `0` không có evidence, `1` có nhưng thiếu điều kiện/nguồn, `2` có đủ evidence và nguồn. Báo phân bố và lý do kèm trace; báo lỗi hệ thống riêng, thấy được mẫu số/test coverage. |
| **Grounded answer** | Câu có đáp án: `0` sai/thiếu evidence hoặc từ chối; `1` đúng một phần; `2` đúng, đủ và bám evidence. Báo phân bố và trung bình trên thang 2. Đọc cả 5+2 câu test ở mỗi cấu hình; ghi lỗi system và số câu chấm được, không dùng mẫu số thu hẹp mà không công bố. |
| **Citation hợp lệ / độ phủ** | Citation vừa có trong context vừa thực sự hỗ trợ mệnh đề / tổng citation; nếu không có, `0/0 (không áp dụng)`. Báo thêm số câu trả lời có citation / tổng số câu đã trả lời. Đọc đơn vị, điều kiện và phép tính, không lấy ID trùng làm kết luận. |
| **Abstention** | Số câu thiếu evidence được từ chối đúng, không đoán / tổng câu thiếu evidence; từ chối nhầm / tổng câu có đáp án. Báo riêng số lỗi mỗi nhóm, kèm mẫu số nếu xuất thêm phiên bản chỉ trên lượt chạy thành công. |
| **Tool use và tài nguyên** | Số case gọi retrieval / số case chạy thành công; phân bố lượt, số retry, timeout và lỗi. Đo thời gian retrieval/agent end-to-end và p50/p95 với cách warm-up/cache cố định; log thời gian index riêng. Ghi token input/output, ảnh nếu có, chi phí API theo lần thử và tổng USD hoặc giải thích `0 USD API` khi chạy local cùng phần cứng/thời gian. |

1. Trước thí nghiệm, công bố cách chọn cấu hình: ưu tiên số grounded answer mức 2 và số abstain đúng trên dev (đếm mọi case, lỗi là không đạt cho **điểm chọn**), lần lượt xét Context Evidence Rate, Evidence Hit@3, Hit@1, p95, chi phí; nếu vẫn hòa, dùng thứ tự ID cố định. Chốt cách tính p95 và chính sách cache/retry. Phần nâng cao chọn riêng theo tỷ lệ pass nghiêm ngặt trên dev, xem từng nhóm rồi dùng chi phí/độ trễ làm điểm phân xử đã ghi trước. Đây là tiêu chí thiết kế, không thay rubric gốc.
2. Với **ít nhất hai lỗi dev thật**: ghi `query_id`, kết quả mong đợi, evidence gốc, rank trước/sau, phần context mất, câu trả lời/citation trước/sau, nguyên nhân, thay đổi, latency/token/chi phí và giới hạn. Phân loại lỗi ở tầng retrieval, packer, trả lời, citation, abstain hoặc hạ tầng. Báo cả giả thuyết sai, cấu hình giảm điểm và nhóm có ít mẫu. Không dùng lỗi fixture hoặc test để thay hai lỗi dev.
3. Lập `artifacts/base/freeze.json` gồm commit code, hash dev/test và corpus/index, model ID/revision, params sinh, prompt/tool schema, filter, packer, budget, retry, timeout, quy tắc chấm, lựa chọn, baseline và thời điểm UTC. Lưu bằng chứng kết quả dev làm căn cứ chọn. Runner test xác nhận lock trước khi chạy; ghi hash vào từng run. Cố định baseline và cấu hình chọn rồi chạy hai cấu hình trên **cùng 7 câu holdout**, không ghi đè run hoặc bỏ lượt lỗi. Nếu cấu hình chọn trùng baseline, ghi rõ hai vai trò và cùng kết quả hoặc chạy đối chứng theo giao thức đã khóa, không giả có cải thiện.
4. Review toàn bộ test của baseline và cấu hình chọn. Chấm `0/1/2` cho cả context và câu trả lời ở 5 case có đáp án, chấm abstention ở 2 case thiếu evidence, chấm từng citation. Lưu `query_id`, `run_id`, nhãn, lý do, vị trí nguồn và tham chiếu trace. Nếu xem test rồi chỉnh retrieval, prompt, parser, evidence, cấu hình hoặc dùng kết quả đó để chọn, giữ trace lịch sử, tạo holdout độc lập mới đúng tỉ lệ và khóa lại; không báo test cũ như kết quả độc lập.

**Qua mốc:** có số liệu `n/N` và tỷ lệ ở mọi mục phù hợp, nhãn test cho cả hai cấu hình, giải thích chênh lệch bằng trace và lock có thời điểm trước test. Không có điều kiện phải vượt 90% ở phần cơ bản.

## 7. Mốc 5 — phần nâng cao: PDF, bằng chứng theo vùng và test ≥90%

**Nguồn đề xuất đã xác minh:** [Landsat 8 Data Users Handbook — USGS](https://www.usgs.gov/media/files/landsat-8-data-users-handbook), *LSDS‑1574*, v5.0, 11/2019. [Bản PDF từ trang USGS](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/LSDS-1574_L8_Data_Users_Handbook-v5.0.pdf) có **114 trang PDF**, gồm phần đầu và **106 trang đánh số** theo [tài liệu dẫn chiếu của USGS](https://pubs.usgs.gov/publication/ofr20221072/full). Mục lục có bảng thông số/QA, hình thiết bị và bố trí cảm biến, biểu đồ hiệu năng và hiệu chuẩn. Nội dung bám đúng snapshot năm 2019, không dùng như mô tả hiện hành của nhiệm vụ Landsat. Trang phát hành ghi Public Domain; vẫn ghi công USGS, kiểm chú thích từng hình và làm theo [chính sách về nội dung bên thứ ba](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits) trước khi nộp crop hoặc chuyển xử lý. Người chấm lấy bản gốc từ URL; không cần commit PDF. Ghi SHA‑256 từ file đã tải trong lúc triển khai.

### 7.1. Lập chỉ mục toàn bộ tài liệu

1. Khởi động việc kiểm quyền và chạy thử trích xuất ngay khi bắt đầu phần cơ bản. Trước khi chọn PDF chính thức, kiểm vài trang đại diện của cả bốn dạng: text, bảng nhiều dòng, ảnh/sơ đồ và đồ thị. Nếu PDF không tải được qua đường chính thức hoặc không thể xác minh đủ vùng hình/bảng theo quyền sử dụng, đổi tài liệu **trước** khi chốt benchmark; xác minh lại mọi điều kiện ≥100 trang.
2. Duyệt **114/114 trang PDF**. Tạo `page_inventory.jsonl` kê `pdf_page`, `printed_label`, mục, các dạng nội dung, số element trích/index, tình trạng và lý do bỏ qua. Tính độ phủ theo trang hữu ích và theo từng loại, không chỉ đếm file. Giữ vùng bảng/hình vẽ vector bằng render theo bbox; đừng giả định mọi hình là ảnh nhúng. Đánh dấu trang trống, trang trang trí hoặc lỗi và giải thích ảnh hưởng; index nội dung hữu ích ngoài benchmark, bao gồm các phụ lục có thông tin.
3. Text: giữ heading và thứ tự đọc, OCR cho vùng text thiếu/bị lỗi. Bảng: trích theo hàng/cột, giữ header nhiều tầng, đơn vị, chú thích, dòng nối trang, tọa độ ô và crop khi cần. Ảnh/sơ đồ: trích crop, caption và nhãn nhìn được; mô tả các đối tượng, vị trí và liên hệ có trong hình. Biểu đồ: ưu tiên dữ liệu gốc nhận được hợp lệ; nếu chỉ có hình, giữ trục/đơn vị/chú giải và crop; ghi dung sai xác định trước cho giá trị đọc từ hình, tránh gán độ chính xác giả. Lưu phương pháp trích, phiên bản parser/OCR/vision, DPI và hệ tọa độ bbox; QA bằng PDF gốc cho các loại và ưu tiên vùng phức tạp có dấu hiệu sai.
4. Thiết lập collection nâng cao riêng trên cùng framework nếu phù hợp. Mỗi element có `evidence_id`, `doc_id`, `pdf_page` (1-based), `printed_label`, bbox, `element_type`, `section`, `crop_ref`, `content`, hash, nguồn và provenance trích xuất. Index dense trên phần text và cách biểu diễn bảng/hình/đồ thị; lexical trên tên, nhãn, đơn vị và caption. Dùng bản mô tả để tìm candidate; khi trả lời câu nhìn hình, cấp đúng crop cho model vision hoặc cấp cách đọc đã đối chiếu có tọa độ. Cho agent dùng `search` và `open_region(evidence_id)` hoặc công cụ tương đương, chỉ mở vùng thực từ index; có thể tìm lần hai để bổ sung bảng/hình khác. Khóa quy tắc join theo thực thể, phiên bản, đơn vị; validate phép tính bằng số trích có nguồn. Index/crop không được chứa gold hoặc bản tóm tắt soạn từ câu hỏi benchmark.
5. Tạo trang/vùng tham chiếu có thể kiểm: một citation trả qua registry phải mở đúng `pdf_page` và xác định được bbox, figure/table/row/column. Chụp/render lại theo script khi không chia sẻ crop. Kiểm trực tiếp một mẫu từng loại và mọi bằng chứng được dùng để chấm test. Không lấy mô tả sinh tự động làm chuẩn cho câu hỏi về ảnh/biểu đồ.

### 7.2. Benchmark riêng và tiêu chí đạt

| Nhóm chính | Dev đề xuất | Test đã lên kế hoạch | Tiêu chí evidence khi gán nhóm |
|---|---:|---:|---|
| Bảng | 4 | **6** | Đọc ô/hàng/cột, đầy đủ header, điều kiện và đơn vị; chọn câu thực sự cần bảng. |
| Ảnh, sơ đồ | 4 | **5** | Vùng hình chứa thông tin cần nhận diện/giải thích, không dùng hình trang trí hoặc chỉ hỏi lại caption. |
| Biểu đồ | 4 | **5** | Cần đọc trục, chú giải, đơn vị, xu hướng hoặc giá trị; dung sai xác định trước. |
| Multi-hop | 4 | **4** | Ít nhất hai vùng/trang/bảng/hình độc lập đều cần thiết để suy ra đáp án; audit từng bước. |
| Text | 4 | **4** | Đoạn nguồn có đủ điều kiện để xác minh câu trả lời. |
| Thiếu bằng chứng | 6 | **6** | Gần chủ đề tài liệu, không đủ căn cứ sau khi rà các phần liên quan; nêu cách kiểm tra. |
| **Tổng** | **26** | **30** | Một nhóm chính mỗi câu; tag phụ không dùng để tính quota. |

- Làm dev trước theo lộ trình so sánh text/caption rồi thử bổ sung crop/vision, hoặc thêm truy xuất theo nhóm/trang. Giữ dev đa dạng và báo kết quả từng nhóm. Mục tiêu nội bộ trước freeze: dev có biên trên ngưỡng 90% (ví dụ ≥24/26) và không có nhóm lỗi hệ thống; đây là tín hiệu sẵn sàng, không phải dự đoán hay thay thế điểm test.
- Freeze riêng `artifacts/advanced/freeze.json` như §6, kèm hash PDF/index, inventory, parser/OCR/vision, routing crop, phép tính và tolerance. Chạy **toàn bộ** 30 câu đã khóa. Mỗi câu có verdict nhị phân và trace. Câu có đáp án chỉ đạt nếu đúng **đủ**, đúng đơn vị/điều kiện/phép tính, citation xác định được trang **và vùng**, và nguồn hỗ trợ toàn bộ lời đáp. Đúng một phần, từ chối, sai vùng hoặc thiếu citation cần thiết → fail. Câu thiếu evidence chỉ đạt nếu nói không đủ bằng chứng và không suy đoán. Timeout, lỗi và không có đầu ra → fail, vẫn nằm trong tổng.
- Người làm đọc bản PDF gốc, ghi từng câu `pass`, `reason`, `failure_type`, citation/vị trí, nguyên văn giá trị kiểm được hoặc phép tính, `reviewer` và timestamp. LLM judge chỉ hỗ trợ. Báo `n/N` của cả 6 nhóm và toàn bộ; giữ lỗi, token, latency và chi phí theo case/nhóm. Với 30 câu, **27 đạt là ngưỡng tối thiểu**; 26/30 không đạt. Nếu chốt hơn 30, ngưỡng là `ceil(0.90 × N)` và tính mọi câu đã chốt, không bỏ nhóm hoặc làm tròn để qua.
- Nếu test đầu dưới 90%: giữ và báo kết quả thật. Chỉ cải tiến trên dev; bất kỳ kết quả test nào dùng để chỉnh sẽ làm test đó mất tính độc lập. Sau thay đổi, chốt lại rồi đánh giá trên **holdout mới** đủ toàn bộ quota, không thay riêng các câu sai. Báo cả lần không đạt và lý do dùng bộ mới. Nếu chưa có lần đánh giá độc lập đạt ngưỡng, chưa có cơ sở tính 15 điểm.

**Qua mốc:** inventory toàn tài liệu, cấu hình lập chỉ mục và quyền sử dụng, lock trước test, đủ nhãn gốc/trace mọi câu, đọc lại bộ evidence theo vùng, và tỷ lệ ≥90% theo số đếm nguyên.

## 8. Mốc 6 — bộ nộp, chạy lại và review cuối

| Đường dẫn dự kiến trong repo | Nội dung cần nộp |
|---|---|
| `src/day07/`, `tests/`, `configs/`, `requirements-lock.txt`, `.env.example` | Adapter Day 6, retriever dense/lexical/hybrid, agent, packer, index PDF, benchmark/scorer, verifier, config baseline/cải tiến/chốt; biến mẫu không chứa giá trị secret. |
| `benchmarks/base/`, `benchmarks/advanced/` | Queries và gold tách theo split; schema, manifest, quy tắc chấm, thống kê nhóm, cách kiểm tra evidence và lý do vắng. |
| `artifacts/base/`, `artifacts/advanced/` | Manifest, hashes, config freeze, inventory/index stats, trace và summary của các lần chạy, audit nhãn, hai lỗi dev trước/sau. Dùng `run_id` để không ghi đè. |
| `README.md`, `report/individual/2A202604113_PhamTranQuoc.md` | Hướng dẫn cài đặt Windows, data/model/DB/PDF, lệnh theo đúng thứ tự, format output, bảng kết quả, chi phí/giới hạn, kết luận và đường dẫn hiện vật. Điền theo `REPORT_TEMPLATE.md`. |

Mỗi dòng trace cần nối được từ `query_id`/`run_id` → config và model → query gốc/tool args/filter/queries viết lại → kết quả/thứ hạng/điểm/vùng → context thực gửi → answer/citation/stop reason → nhãn và lý do. Ghi cả số lượt, lỗi, time/token/chi phí. Báo cáo có ít nhất một ví dụ trả lời có evidence, một trường hợp thiếu bằng chứng và một lỗi có giải thích; cho giảng viên mở được nguồn từ cả ba ví dụ. Giữ link tương đối trong báo cáo và hướng dẫn lấy tài liệu; việc tái lập không phụ thuộc đường dẫn máy cá nhân.

Trong lúc làm, dùng lệnh starter thật để kiểm khói:

```powershell
$env:PYTHONUTF8 = '1'
python -m unittest discover -s tests -v
python starter/baseline.py --chunks data/example_chunks.json --questions data/example_questions.json --split dev --output starter/results/example-dev
```

Khi viết phần triển khai, README phải có các lệnh thật để: kiểm prerequisite → nhập/khôi phục Day 6 → lập chỉ mục PDF → validate benchmark → chạy dev cả hai bộ → khóa độc lập → chạy baseline/chosen test cơ bản và full test nâng cao → ghép review → lập bảng → audit gói nộp. Thử quy trình từ một checkout sạch với quyền truy cập tương đương người chấm, tường trình sai số khi chạy lại model sinh. Kiểm `git ls-files` và phạm vi diff để chắc bài nộp có trace/nhãn cần thiết; dùng repo cá nhân và xác nhận quyền xem trước khi nộp link, đừng dùng remote đề bài. Không commit venv, snapshot model, DB/crop không được chia sẻ, log chứa secret, `.env` hoặc token. Xem `SUBMISSION.md` để xác nhận tên repo và cách nộp theo lớp.

### Checklist chốt bài

- [ ] **13/13:** đã kết nối E5/Qdrant Day 6 thật, ghi nguồn và quyền; 30 câu cơ bản theo phương án §4 hoặc ít nhất 24 đúng tỉ lệ, gold và split được kiểm.
- [ ] **17/17:** có 3 phương pháp thực sự khác nhau, báo top-3 của query gốc trên cùng dev, score/rank và filter/lỗi có trace.
- [ ] **17/17:** model thật gọi tool; context, citation, abstain, giới hạn lượt và trường hợp lỗi kiểm được.
- [ ] **17/17:** đủ bảng retrieval/context/agent. Người làm đã chấm ≥5 case answerable và ≥2 case thiếu evidence trên cùng test cho D0 và cấu hình chọn; có nhãn từng citation.
- [ ] **13/13:** đo ≥2 cải tiến, ≥2 lỗi dev trước/sau, công bố tiêu chí, lock trước test và nêu đánh đổi chất lượng, thời gian, chi phí.
- [ ] **8/8:** có lệnh tái lập, model/data version và báo cáo đúng tên; kiểm artifact và quyền xem repo.
- [ ] **15/15 nâng cao:** index một PDF ≥100 trang và audit độ phủ; dev/test riêng đúng quota; nhãn/trace đối chiếu bản gốc cho **mọi** câu; lỗi nằm trong mẫu số và đạt **≥27/30** nếu `N=30`.

### Kết luận review và thứ tự ưu tiên

1. Kết nối `lab6_B`, sửa lỗi UTF‑8 của test, xác minh model sinh thật và chốt kế hoạch benchmark. Thử parser và crop trên vài trang PDF đại diện để phát hiện sớm lỗi bảng và biểu đồ.
2. **Trước khi nhìn test:** chốt câu hỏi/gold, chạy đủ cấu hình dev, đọc lỗi, đo chi phí, chọn và lưu freeze cho từng phần. Đừng dùng các kết quả Day 6 làm số liệu Day 7. Phần cơ bản có đường triển khai tốt vì Day 6 đã probe được thật; chưa có bằng chứng agent Day 7 hoạt động.
3. **Rủi ro lớn nhất đối với 100/100:** mục nâng cao chỉ có biên 3 câu sai ở bộ 30. Các điểm dễ hỏng là bảng thiếu header/đơn vị, model đọc sai chú giải, citation đúng trang sai vùng, multi-hop thiếu một nguồn và timeout API. Khống chế các lỗi này trên **dev**, chuẩn hóa trace và kiểm trực tiếp mọi nhãn test trước khi tự đánh dấu 15/15.
4. **Chốt nộp:** audit link, artifact, quyền và bảng tự chấm; báo trung thực hạng mục chưa đủ. 15 unit test starter pass ở chế độ UTF‑8 chỉ là kiểm chứng code mẫu. Điểm tối đa do giảng viên quyết định từ bài nộp, không thể suy ra từ kế hoạch hoặc smoke test.
