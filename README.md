# Day 7 — Agentic RAG

Lab cá nhân nối tiếp Day 6. Repo có dense retrieval trên Qdrant/E5, TF-IDF, hybrid RRF, agent tool-calling chạy model cục bộ, benchmark tách queries/gold, trace và báo cáo. **Phần cơ bản đã chạy dev/test; test nâng cao đạt 24/30 theo review có hỗ trợ AI, dưới ngưỡng 27/30 để nhận 15 điểm.** Xem [báo cáo chi tiết](report/individual/2A202604113_PhamTranQuoc.md), [rubric](RUBRIC.md), [benchmark](BENCHMARK.md) và [yêu cầu nâng cao](ADVANCED.md).

Không đưa gold vào agent. `page` của corpus Day 6 là đơn vị RST, không phải trang PDF. Citation ID hợp lệ không đủ chứng minh câu trả lời được hỗ trợ; các nhãn hiện tại do Codex hỗ trợ, cần kiểm tra độc lập trước khi nộp.

## Chuẩn bị trên Windows

1. Cần Python 3.12.10, repo Day 6 có `src/embeddings.py`, `src/store.py`, E5 snapshot `intfloat/multilingual-e5-small` revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, và các license của CPython. Có thể tái tạo snapshot theo README Day 6. Phiên bản đã dùng được pin trong [requirements-lock.txt](requirements-lock.txt). Tạo venv riêng và cài dependency, hoặc dùng venv Day 6 tương thích; chỉ cài PyMuPDF nếu chạy phần PDF.

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
   $env:PYTHONUTF8 = '1'
   $Py = (Resolve-Path '.\.venv\Scripts\python.exe').Path
   $Day6Root = (Resolve-Path '..\K5-L3B-DAY06-2A202604113-DataIngestion').Path
   $E5Model = Join-Path $Day6Root '.local\model-snapshot'
   ```

   Nếu tên/thư mục Day 6 khác, thay `$Day6Root`. Không cần đưa `.env`, venv hay model weights vào repo; [.env.example](.env.example) chỉ mô tả các giá trị mẫu.

2. Phục hồi Qdrant **chưa tồn tại** từ [archive được phép chia sẻ](artifacts/base/qdrant-snapshot.zip), hoặc tạo bản sao mới từ Day 6 khi không có writer. Archive giữ byte/hash khớp lock test; xây lại SQLite từ đầu có thể cho hash khác dù nội dung logic giống nhau.

   ```powershell
   New-Item -ItemType Directory -Force '.local' | Out-Null
   Expand-Archive -LiteralPath 'artifacts/base/qdrant-snapshot.zip' -DestinationPath '.local/day6-qdrant-restored'
   $Qdrant = (Resolve-Path '.local/day6-qdrant-restored').Path
   # Tùy chọn: tạo bản sao mới, ghi manifest vào thư mục mới thay vì ghi đè artifact đã nộp:
   & $Py -m src.day07 snapshot --day6-root $Day6Root --qdrant-copy '.local/day6-qdrant-new' --output '.local/day6-audit'
   ```

3. Chạy llama.cpp server cục bộ bản **b12406** với Qwen2.5 7B Instruct Q4_K_M. Bản thử nghiệm dùng [llama.cpp Windows Vulkan release](https://github.com/ggml-org/llama.cpp/releases/tag/b12406) và blob [Ollama qwen2.5:7b](https://ollama.com/library/qwen2.5:7b), SHA-256 `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`. Model không được đóng gói. Sau khi lấy model, kiểm SHA-256; nếu tag đã thay đổi, cần tìm đúng bản theo digest, không tự nhận là cùng run. Kiểm `--list-devices` và chọn GPU phù hợp; trên máy thử là `Vulkan1`. Ví dụ chạy trong một terminal riêng:

   ```powershell
   $Llama = (Resolve-Path '.local/llama/llama-server.exe').Path
   $Model = Join-Path $env:USERPROFILE '.ollama\models\blobs\sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730'
   Get-FileHash -Algorithm SHA256 -LiteralPath $Model
   & $Llama --list-devices
   & $Llama -m $Model --host 127.0.0.1 --port 8085 --device Vulkan1 --n-gpu-layers 99 --ctx-size 4096 --threads 8 --parallel 1 --jinja --alias qwen2.5-7b-local
   ```

   Thay device hoặc dùng CPU khi không có GPU tương thích. Endpoint chỉ bind loopback; không đưa secret vào log. Thời gian và câu trả lời có thể thay đổi theo phần cứng/bản runtime.

## Kiểm tra và chạy phần cơ bản

```powershell
& $Py -m unittest discover -s tests -v
& $Py starter/baseline.py --chunks data/example_chunks.json --questions data/example_questions.json --split dev --output starter/results/example-dev
& $Py -m src.day07 validate --split dev
& $Py -m src.day07 validate --split test
```

Starter fixture chỉ kiểm khói, không phải kết quả lab. Để chạy lại dev, chọn `run-id` mới; runner không ghi đè và không đưa gold vào model:

```powershell
& $Py -m src.day07 run --day6-root $Day6Root --qdrant $Qdrant --model-path $E5Model --config D0,L0,H0,H1,H2,H3 --split dev --run-id my-dev-01
& $Py -m src.day07 score --split dev --traces artifacts/base/runs/my-dev-01/H0.jsonl --output artifacts/base/my-dev-H0-metrics.json
```

Code [review dev](scripts/review_base_dev.py) ghi nhãn cho các trace đã nộp, không tự chấm run mới. Trước test mới phải review dev, áp dụng tiêu chí trong cấu hình và khóa dữ liệu/model/code. Lock đã nộp là [freeze.json](artifacts/base/freeze.json); nó yêu cầu đúng hash model, E5, Day 6, Qdrant, code và benchmark. Chạy lại **đúng pipeline đã khóa**, dùng run ID khác, không dùng kết quả test để chọn lại:

```powershell
& $Py -m src.day07 run --day6-root $Day6Root --qdrant $Qdrant --model-path $E5Model --config D0,H0 --split test --run-id my-test-01 --lock artifacts/base/freeze.json
& $Py -m src.day07 score --split test --traces artifacts/base/runs/my-test-01/D0.jsonl --output artifacts/base/my-test-D0-metrics.json
```

Mỗi dòng JSONL lưu query, scope, ranking query gốc, tool query/results, quyết định pack, context, answer, citation, thời gian/token và lỗi. Scorer retrieval giữ các câu answerable trong mẫu số. Review semantic/citation cần đọc nguồn và ghi nhãn riêng; không coi score hay ID trùng là bằng chứng entailment. Nếu chỉnh pipeline sau khi xem test, phải tạo holdout mới và khóa lại.

## PDF nâng cao: trạng thái và tái tạo vùng

[USGS Landsat 8 Data Users Handbook v5.0](https://www.usgs.gov/media/files/landsat-8-data-users-handbook) có 114 trang; file PDF SHA-256 `baf10fd32ebbc5d21a509869e2879f5ef23f0d275d8bddc01462ed02d18bc756`. Trang nguồn ghi Public Domain, nhưng cần xét quyền của từng hình bên thứ ba. PDF/crop không nằm trong repo.

```powershell
New-Item -ItemType Directory -Force '.local/downloads' | Out-Null
curl.exe -L --fail 'https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/LSDS-1574_L8_Data_Users_Handbook-v5.0.pdf' -o '.local/downloads/landsat8-v5.pdf'
Get-FileHash -Algorithm SHA256 '.local/downloads/landsat8-v5.pdf'
# Dùng thư mục mới để tránh ghi đè inventory đã nộp:
& $Py -m src.day07.pdf_index build --pdf '.local/downloads/landsat8-v5.pdf' --output '.local/advanced-rebuild'
& $Py -m src.day07.pdf_index render-region --pdf '.local/downloads/landsat8-v5.pdf' --index artifacts/advanced/elements.jsonl --evidence-id landsat-v5-p016-image-001 --output '.local/figure-2-1.png'
& $Py -m scripts.validate_advanced --split dev
& $Py -m scripts.validate_advanced --split test
```

[Inventory/QA](artifacts/advanced/qa_samples.md), [benchmark dự thảo](benchmarks/advanced/manifest.json) và [index có OCR v4](artifacts/advanced/search_manifest-v4.json) được giữ. OCR chạy trên 77 vùng ảnh/vector, trong đó 10 vùng không nhận chữ; OCR và bảng trích xuất chưa được xác minh toàn bộ. Index này chưa chứng minh hiểu toàn bộ ảnh/biểu đồ; câu thiếu evidence cần audit cả nội dung trực quan.

[Index v5 bổ sung](artifacts/advanced/search-manifest-v5-supplement.json) thêm mô tả định tính do Codex quan sát cho 10 vùng OCR rỗng và được dùng trong A4/A5. [Kiểm tra cấu trúc](artifacts/advanced/index-coverage-v5.json) thấy 114/114 trang và 852/852 vùng ứng viên có đoạn tìm kiếm; chất lượng ngữ nghĩa hình vẫn cần kiểm. Mã retrieval hiện đã sửa câu cảnh báo về OCR/mô tả; [snapshot mã A1](artifacts/advanced/code-snapshots/a1/advanced_retrieval.py) giữ nguyên phiên bản trong manifest cũ.

Để tái tạo OCR và index trong đường dẫn mới (RapidOCR có thể cần tải model lần đầu; đối chiếu hash model với [provenance](artifacts/advanced/ocr-provenance.json)):

```powershell
& $Py -m pip install -r requirements-ocr-lock.txt
& $Py -m scripts.ocr_pdf_regions --pdf '.local/downloads/landsat8-v5.pdf' --elements artifacts/advanced/elements.jsonl --output '.local/ocr-rebuild.jsonl'
& $Py -m src.day07.advanced_retrieval --day6-root $Day6Root --model-path $E5Model --elements artifacts/advanced/elements.jsonl --ocr artifacts/advanced/ocr-regions-v1.jsonl --qdrant '.local/advanced-qdrant-rebuild' --chunks-output '.local/advanced-chunks-rebuild.jsonl' --output '.local/advanced-index-rebuild.json'
# Tùy chọn: tái tạo phiên bản với mô tả 10 vùng OCR rỗng trong đường dẫn mới:
& $Py -m scripts.describe_empty_ocr --elements artifacts/advanced/elements.jsonl --ocr artifacts/advanced/ocr-regions-v1.jsonl --descriptions '.local/my-visual-descriptions.jsonl' --elements-output '.local/my-elements-described.jsonl'
& $Py -m src.day07.advanced_retrieval --day6-root $Day6Root --model-path $E5Model --elements '.local/my-elements-described.jsonl' --ocr artifacts/advanced/ocr-regions-v1.jsonl --qdrant '.local/advanced-qdrant-described' --chunks-output '.local/advanced-chunks-described.jsonl' --output '.local/advanced-index-described.json'
```

Thí nghiệm A1 dùng [Qwen2.5-VL-3B-Instruct-GGUF](https://huggingface.co/ggml-org/Qwen2.5-VL-3B-Instruct-GGUF/tree/5037fcf163dd95d1e41d1974465f0898ed108ca2), phiên bản Q4_K_M SHA-256 `d02fe9b69ad8cadbbd228e387667af66612c44bed29ffc8eb1e7caf9ac486c12`, projector Q8_0 SHA-256 `980c9b2f78c04e6cff93d277ada09e768394f112d75db3b4e9dea8a69f9fb904`. Tải hai file theo revision này, kiểm tra hash, rồi chạy server cục bộ ở terminal riêng; không đưa weights vào repo. Thay `Vulkan1` nếu máy dùng device khác:

```powershell
$Llama = (Resolve-Path '.local/llama/llama-server.exe').Path
$VisionModel = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-q4.gguf').Path
$VisionProjector = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-mmproj-q8.gguf').Path
Get-FileHash -Algorithm SHA256 $VisionModel, $VisionProjector
& $Llama -m $VisionModel --mmproj $VisionProjector --host 127.0.0.1 --port 8086 --device Vulkan1 --n-gpu-layers 99 --ctx-size 8192 --image-min-tokens 1024 --image-max-tokens 1024 --threads 8 --parallel 1 --jinja --alias qwen2.5-vl-3b-local
```

Ở terminal chạy lab, thử lại dev với run ID mới. Runtime không đưa gold vào model; model tạo JSON action và dispatcher kiểm tra handle, không phải native tool API của vision server:

```powershell
$VisionProjector = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-mmproj-q8.gguf').Path
& $Py -m scripts.run_advanced --split dev --run-id my-advanced-dev-01 --day6-root $Day6Root --model-path $E5Model --qdrant '.local/advanced-qdrant-rebuild' --chunks '.local/advanced-chunks-rebuild.jsonl' --ocr artifacts/advanced/ocr-regions-v1.jsonl --projector $VisionProjector --pdf '.local/downloads/landsat8-v5.pdf'
```

Review theo nguồn của Codex cho A0 đạt 6/26, A1 đạt 8/26 trên dev, tính cả lỗi và citation không hỗ trợ; lần A1 bị gián đoạn sau câu 15 và được tiếp tục cho 11 câu còn lại mà không chạy lại lỗi. Thí nghiệm A2 hiệu đính bằng model chữ đạt 17/26 sau chuẩn hóa, A3 phân nhánh đạt 21/26; hai pilot dùng lại trace. A5 chạy lại chuỗi nhiều giai đoạn trên index v5 đạt 25/26 dev theo review có hỗ trợ AI, có sáu lỗi định dạng ở tầng vision đã được xử lý và không có timeout. Xem [chi tiết và giới hạn](report/individual/2A202604113_PhamTranQuoc.md).

Để tái tạo riêng pilot A2, chạy server Qwen2.5 7B ở cổng 8085 như phần cơ bản, rồi dùng đường dẫn output mới:

```powershell
& $Py -m scripts.refine_advanced_dev --trace artifacts/advanced/runs/advanced-dev-20261115-a1/traces.jsonl --trace artifacts/advanced/runs/advanced-dev-20261115-a1-continuation-v2/traces.jsonl --output '.local/my-a2-pilot'
& $Py -m scripts.revalidate_advanced_refiner --trace '.local/my-a2-pilot/traces.jsonl' --output '.local/my-a2-normalized'
& $Py -m scripts.modality_policy_dev --vision-trace artifacts/advanced/runs/advanced-dev-20261115-a1/traces.jsonl --vision-trace artifacts/advanced/runs/advanced-dev-20261115-a1-continuation-v2/traces.jsonl --refined-trace '.local/my-a2-normalized/traces.jsonl' --output '.local/my-a3-pilot'
```

Pipeline A5 được [khóa](artifacts/advanced/freeze-composite.json) trước test, gồm hash hai model, projector, mã, benchmark và Qdrant. Để tái chạy đúng index đã khóa, phục hồi [snapshot Qdrant v5](artifacts/advanced/qdrant-v5-snapshot.zip) vào một thư mục mới; không dựng SQLite mới nếu cần khớp hash byte của lock:

```powershell
Expand-Archive -LiteralPath 'artifacts/advanced/qdrant-v5-snapshot.zip' -DestinationPath '.local/advanced-qdrant-restored'
$AdvancedQdrant = (Resolve-Path '.local/advanced-qdrant-restored').Path
$VisionModel = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-q4.gguf').Path
$VisionProjector = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-mmproj-q8.gguf').Path
# Bước 1: chạy vision server ở 8086 như trên, rồi chạy đủ test:
& $Py -m scripts.run_advanced --split test --run-id my-advanced-test-vision --day6-root $Day6Root --model-path $E5Model --qdrant $AdvancedQdrant --chunks artifacts/advanced/search_chunks-v5.jsonl --ocr artifacts/advanced/ocr-regions-v1.jsonl --pdf '.local/downloads/landsat8-v5.pdf' --projector $VisionProjector --lock artifacts/advanced/freeze-composite.json
# Bước 2: dừng vision server; trong terminal riêng chạy Qwen2.5 7B với context 8192 như thí nghiệm:
$TextModel = Join-Path $env:USERPROFILE '.ollama\models\blobs\sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730'
& $Llama -m $TextModel --host 127.0.0.1 --port 8085 --device Vulkan1 --n-gpu-layers 99 --ctx-size 8192 --threads 8 --parallel 1 --jinja --alias qwen2.5-7b-local
# Ở terminal lab, sau khi server text sẵn sàng:
& $Py -m scripts.run_composite_final --split test --vision-run artifacts/advanced/runs/my-advanced-test-vision --output artifacts/advanced/runs/my-advanced-test-final --day6-root $Day6Root --model-path $E5Model --qdrant $AdvancedQdrant --chunks artifacts/advanced/search_chunks-v5.jsonl --ocr artifacts/advanced/ocr-regions-v1.jsonl --pdf '.local/downloads/landsat8-v5.pdf' --projector $VisionProjector --vision-model $VisionModel --lock artifacts/advanced/freeze-composite.json
```

Hai bước trên không đưa gold vào model hoặc dùng gold để chọn evidence. Bước kiểm lock có đọc byte của file gold để tính hash phát hiện thay đổi; câu “gold is not read” trong manifest là cách diễn đạt chưa chính xác ở mức filesystem. Lock kiểm hash model, projector, dữ liệu và mã, nhưng không tự kiểm chứng toàn bộ tham số server hoặc projector thực sự đã nạp; phải đối chiếu lệnh chạy và bản llama.cpp b12406. [Test đã chạy](artifacts/advanced/test-summary-composite.json) đạt 24/30, chưa đạt ngưỡng 27/30; [review từng câu](artifacts/advanced/test-review-composite.jsonl) cần được người làm/giảng viên kiểm tra lại. Nếu thay đổi theo kết quả test, phải tạo và khóa test độc lập mới.

## Nộp

Kiểm [báo cáo](report/individual/2A202604113_PhamTranQuoc.md), trace, nhãn, hash, license và `git status --short --untracked-files=all`; thêm các file cần nộp vào repo cá nhân rồi kiểm `git ls-files`. Không đưa `.local`, venv, weights, token hay dữ liệu mật vào commit. Làm theo [SUBMISSION.md](SUBMISSION.md) và xác nhận người chấm có quyền truy cập.

## Runbook v? x?c nh?n ngu?n hi?n t?i

Xem [chu?i l?nh ??y ??](docs/REPRODUCE.md) t? chu?n b?, dev, review, freeze ??n test v? score. [Metrics c? b?n ??y ??](artifacts/base/submission-metrics.json) c? ph?n b? l??t g?i tool cho c? c?u th?nh c?ng v? l?i. [Metrics n?ng cao v1](artifacts/advanced/test-summary-v1-author-confirmed.json) b? sung th?i gian/token/chi ph? theo t?ng case v? nh?m; k?t qu? v?n 24/30. C?c manifest PARTIAL/PROVISIONAL c? ghi tr?ng th?i l?c tr?ch xu?t; [audit hi?n t?i](artifacts/advanced/index-audit-author-confirmed.json) v? [bi?n b?n t?c gi?](artifacts/source-verification.json) l? tr?ng th?i ki?m ch?ng ngu?n m?i nh?t.
