# Tái lập bài nộp Day 7

## Điều kiện và nguồn

- Python 3.12.10; cài `requirements-lock.txt`. OCR chỉ cần nếu tái tạo OCR: cài thêm `requirements-ocr-lock.txt`.
- Repo Day 6 có `src/embeddings.py`, `src/store.py`; E5 snapshot `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`. Manifest và license nằm trong `artifacts/base/`.
- llama.cpp b12406 Windows Vulkan. Dùng các model và projector đúng digest trong các lock. README chỉ rõ nguồn tải; weights, PDF, venv và `.env` không được commit.
- PDF Landsat 8 v5.0: 114 trang, SHA-256 `baf10fd32ebbc5d21a509869e2879f5ef23f0d275d8bddc01462ed02d18bc756`.
- Tác giả đã xác nhận kiểm chứng toàn bộ nguồn: [biên bản](../artifacts/source-verification.json). Đây là xác nhận nguồn; kết quả model vẫn được chấm theo trace thực tế.
- `.gitattributes` giữ nguyên byte của các đầu vào đã băm (code runtime, cấu hình, benchmark, artifact và dependency lock), tránh Git tự đổi LF/CRLF trên Windows; các văn bản khác dùng LF.

## Chuẩn bị PowerShell

Chạy tại root của một checkout. Đặt các đường dẫn phù hợp với máy; không sửa mã để đổi đường dẫn.

```powershell
$env:PYTHONUTF8 = '1'
$Py = (Resolve-Path '.venv/Scripts/python.exe').Path
$Day6Root = (Resolve-Path '../K5-L3B-DAY06-2A202604113-DataIngestion').Path
$E5Model = Join-Path $Day6Root '.local/model-snapshot'
$Pdf = (Resolve-Path '.local/downloads/landsat8-v5.pdf').Path
$VisionModel = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-q4.gguf').Path
$Projector = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-mmproj-q8.gguf').Path
$TextModel = Join-Path $env:USERPROFILE '.ollama/models/blobs/sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730'
Expand-Archive -LiteralPath 'artifacts/base/qdrant-snapshot.zip' -DestinationPath '.local/base-restored'
Expand-Archive -LiteralPath 'artifacts/advanced/qdrant-v5-snapshot.zip' -DestinationPath '.local/advanced-restored'
$Qdrant = (Resolve-Path '.local/base-restored').Path
$AdvancedQdrant = (Resolve-Path '.local/advanced-restored').Path
& $Py -m unittest discover -s tests -v
& $Py -m src.day07 validate --split dev
& $Py -m src.day07 validate --split test
& $Py -m scripts.advanced_release validate --split dev
& $Py -m scripts.advanced_release validate --split test
```

Đích giải nén phải chưa tồn tại. Không có writer khác mở cùng Qdrant local. Snapshot đã đối chiếu payload với export; xây lại SQLite từ đầu có thể có hash byte khác dù cùng nội dung.

## Cơ bản: dev → review → freeze → test → tổng hợp

Khởi động server text đúng lệnh phần cơ bản trong README: context 4096, model alias `qwen2.5-7b-local`, nhiệt độ request 0. Dùng `run-id` và đường dẫn output mới; không ghi đè bài đã nộp.

```powershell
& $Py -m src.day07 run --day6-root $Day6Root --qdrant $Qdrant --model-path $E5Model --config D0,L0,H0,H1,H2,H3 --split dev --run-id reproduce-dev
& $Py -m src.day07 score --split dev --traces artifacts/base/runs/reproduce-dev/H0.jsonl --output .local/reproduce-dev-H0.json
```

Đọc output dev, ghi nhãn từng câu theo schema của `artifacts/base/dev_review.json`: mỗi cấu hình có đủ 23 câu, lý do, điểm grounded hoặc abstention, context, retrieval và thời gian. Chọn cấu hình theo tie-break đã công bố. Các script `review_base_dev.py`/`review_base_test.py` là biên bản cho **trace lịch sử cụ thể**, không phải judge tổng quát cho output mới.

Lệnh freeze đầy đủ (chỉ dùng nhãn khớp đúng run và lựa chọn thực tế):

```powershell
& $Py -m src.day07 freeze --day6-root $Day6Root --qdrant $Qdrant --model-path $E5Model --dev-review .local/reproduce-dev-review.json --chosen H0 --baseline D0 --output .local/reproduce-base-freeze.json
& $Py -m src.day07 run --day6-root $Day6Root --qdrant $Qdrant --model-path $E5Model --config D0,H0 --split test --run-id reproduce-test --lock .local/reproduce-base-freeze.json
& $Py -m src.day07 score --split test --traces artifacts/base/runs/reproduce-test/D0.jsonl --output .local/reproduce-test-D0.json
& $Py -m src.day07 score --split test --traces artifacts/base/runs/reproduce-test/H0.jsonl --output .local/reproduce-test-H0.json
```

Muốn chạy lại đúng pipeline đã nộp, dùng `artifacts/base/freeze.json`. Test đã công bố không được dùng để chọn lại cấu hình; rerun chỉ là tái lập, không chọn kết quả đẹp hơn thay kết quả gốc. Năm câu answerable và hai câu thiếu đều phải được chấm cho cả D0 và H0; lỗi vẫn nằm trong mẫu số. Metrics bổ sung của các trace gốc nằm tại `artifacts/base/submission-metrics.json`.

## Nâng cao v2: dev → review → freeze → toàn bộ test → review → score

V1 giữ nguyên kết quả 24/30. V2 dùng 56 câu cũ làm dev, 30 câu mới làm holdout; quota, giá trị nguồn, điều kiện, phép tính và dung sai được công bố trước chạy model. Không chạy lại builder lên benchmark đã tồn tại.

Khởi động từng server bằng `scripts/start_model_server.ps1`; hai server chạy tuần tự trên máy 16 GB RAM. Helper trả PID của process mới; dừng đúng process đó trước khi chuyển stage. Runtime của release kiểm executable, model/projector và command line thực tế, không chỉ file cấu hình.

```powershell
$Common = @('--day6-root', $Day6Root, '--model-path', $E5Model, '--qdrant', $AdvancedQdrant, '--pdf', $Pdf, '--vision-model', $VisionModel, '--projector', $Projector, '--text-model', $TextModel)
# Terminal server / hoặc chạy helper và lưu PID:
$VisionPid = & ./scripts/start_model_server.ps1 -Stage vision -ModelPath $VisionModel -ProjectorPath $Projector -LogPrefix .local/my-vision
# Chờ /health trả status ok, rồi:
& $Py -m scripts.advanced_release run @Common --stage vision --split dev --output artifacts/advanced/runs/my-v2-dev-vision
Stop-Process -Id $VisionPid
$TextPid = & ./scripts/start_model_server.ps1 -Stage text -ModelPath $TextModel -LogPrefix .local/my-text
# Chờ server sẵn sàng:
& $Py -m scripts.advanced_release run @Common --stage text --split dev --vision-run artifacts/advanced/runs/my-v2-dev-vision --output artifacts/advanced/runs/my-v2-dev-final
```

Review dev phải gắn `trace_sha256` của đúng file mới, nhãn nhị phân, lý do, `failure_type`, giá trị nguồn/phép tính và audit từng citation. Schema có thể tham khảo nhãn đã nộp; không dùng nhãn cũ cho output mới. Sau khi đáp ứng readiness dev và khóa pipeline:

```powershell
& $Py -m scripts.advanced_release score --split dev --traces artifacts/advanced/runs/my-v2-dev-final/traces.jsonl --reviews .local/my-v2-dev-review.jsonl --output .local/my-v2-dev-score.json
& $Py -m scripts.advanced_release freeze @Common --dev-run artifacts/advanced/runs/my-v2-dev-final --reviews .local/my-v2-dev-review.jsonl --output .local/my-v2-freeze.json
Stop-Process -Id $TextPid
$VisionPid = & ./scripts/start_model_server.ps1 -Stage vision -ModelPath $VisionModel -ProjectorPath $Projector -LogPrefix .local/my-test-vision
# Chờ server sẵn sàng; không có --limit cho test:
& $Py -m scripts.advanced_release run @Common --stage vision --split test --lock .local/my-v2-freeze.json --output artifacts/advanced/runs/my-v2-test-vision
Stop-Process -Id $VisionPid
$TextPid = & ./scripts/start_model_server.ps1 -Stage text -ModelPath $TextModel -LogPrefix .local/my-test-text
# Chờ server sẵn sàng:
& $Py -m scripts.advanced_release run @Common --stage text --split test --vision-run artifacts/advanced/runs/my-v2-test-vision --lock .local/my-v2-freeze.json --output artifacts/advanced/runs/my-v2-test-final
```

Đối chiếu từng câu trả lời với bản gốc và đúng trang/vùng được dẫn; ghi nhãn cho **cả 30 câu** rồi tổng hợp:

```powershell
& $Py -m scripts.advanced_release score --split test --traces artifacts/advanced/runs/my-v2-test-final/traces.jsonl --reviews .local/my-v2-test-review.jsonl --output .local/my-v2-test-score.json
Stop-Process -Id $TextPid
```

Scorer tổng hợp nhãn, không tự phán quyết ngữ nghĩa. Đúng một phần, thiếu citation hỗ trợ, từ chối câu có đáp án, lỗi và timeout đều fail. Cần ít nhất 27/30 cùng đủ yêu cầu nguồn/index/benchmark. Nếu dùng output test mới để chỉnh, bộ đó trở thành dev và cần một holdout đầy đủ khác; không đổi riêng câu sai.

### Lượt dev đã nộp và việc tái dùng giai đoạn đọc ảnh

A6/A7/A8 giữ các thử nghiệm prompt chưa tốt. A8 đọc ảnh tự nhiên trên đủ 56 câu; A9 sửa riêng bước kết luận. Lượt dev A9 tái dùng giai đoạn đọc ảnh A8 **không thay đổi** thay vì chạy VLM lại. Runner kiểm byte của snapshot gốc, AST của toàn bộ hàm đọc ảnh/routing, cấu hình liên quan và toàn bộ model/data/dependency; thay đổi ngoài finalizer bị từ chối. Đây là thử nghiệm dev theo giai đoạn, không được mô tả là hai giai đoạn đều vừa chạy mới. Để tái tạo đúng lượt dev này với text server sẵn sàng:

```powershell
& $Py -m scripts.advanced_release run @Common --stage text --split dev --vision-run artifacts/advanced/runs/advanced-v2-dev-a8-vision --reuse-dev-vision-code artifacts/advanced/code-snapshots/a8/src/day07/multimodal_v2.py --output artifacts/advanced/runs/my-a9-dev-final
```

Cờ này bị cấm trên test. Lượt test chính thức chạy mới cả vision và text sau freeze, cùng code/config/model/runtime đã khóa. Có thể chạy dev mới hoàn toàn bằng chuỗi lệnh ở trên.

## Kiểm bài nộp

Chạy kiểm tra submission, kiểm `git diff --check`, thêm file được phép chia sẻ và kiểm `git ls-files`. Không add `.local`, weights, PDF/crop, cache, secret hay dữ liệu không được phép. Commit/push repo cá nhân và kiểm người chấm truy cập được. Báo cáo phải giữ kết quả thí nghiệm không thành công và ghi rõ phạm vi tái lập đã thực hiện.
