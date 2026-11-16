# Tái lập bài nộp Day 7

## Điều kiện và nguồn

- Python 3.12.10; cài `requirements-lock.txt`. OCR chỉ cần nếu tái tạo OCR: cài thêm `requirements-ocr-lock.txt`.
- [Repo Day 6 cá nhân](https://github.com/Quoosc/K5-L3B-DAY06-2A202604113-DataIngestion) public tại commit **19a54c590f2c89198225592f2be9b1a926abdffd**, cung cấp `src/embeddings.py`, `src/store.py`; E5 snapshot `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`. [Provenance code](../artifacts/day6-code-provenance.json) đối chiếu byte của hai module với lock. Manifest và license nằm trong `artifacts/base/`.
- llama.cpp b12406 Windows Vulkan. Dùng các model và projector đúng digest trong các lock. README chỉ rõ nguồn tải; weights, PDF, venv và `.env` không được commit.
- PDF Landsat 8 v5.0: 114 trang, SHA-256 `baf10fd32ebbc5d21a509869e2879f5ef23f0d275d8bddc01462ed02d18bc756`.
- Tác giả đã xác nhận kiểm chứng toàn bộ nguồn: [biên bản](../artifacts/source-verification.json). Đây là xác nhận nguồn; kết quả model vẫn được chấm theo trace thực tế.
- `.gitattributes` giữ nguyên byte của các đầu vào đã băm (code runtime, cấu hình, benchmark, artifact và dependency lock), tránh Git tự đổi LF/CRLF trên Windows; các văn bản khác dùng LF.

## Chuẩn bị PowerShell

Chạy tại root của một checkout. Đặt các đường dẫn phù hợp với máy; không sửa mã để đổi đường dẫn.

Nếu chưa có Day 6, clone vào một thư mục mới cạnh Day 7 và dùng đúng commit. Không chạy lại test Day 6 để tạo số liệu cho Day 7.

```powershell
git -c core.autocrlf=false clone https://github.com/Quoosc/K5-L3B-DAY06-2A202604113-DataIngestion.git ../K5-L3B-DAY06-2A202604113-DataIngestion
git -C ../K5-L3B-DAY06-2A202604113-DataIngestion checkout --detach 19a54c590f2c89198225592f2be9b1a926abdffd
```

```powershell
$env:PYTHONUTF8 = '1'
$Py = (Resolve-Path '.venv/Scripts/python.exe').Path
$Day6Root = (Resolve-Path '../K5-L3B-DAY06-2A202604113-DataIngestion').Path
$E5Model = Join-Path $Day6Root '.local/model-snapshot'
# Chỉ khi chưa có đúng E5 snapshot: tải 10 file theo revision/checksum của Day 6.
& $Py (Join-Path $Day6Root 'scripts/fetch_model.py')
$Pdf = (Resolve-Path '.local/downloads/landsat8-v5.pdf').Path
$TextModel = Join-Path $env:USERPROFILE '.ollama/models/blobs/sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730'
Expand-Archive -LiteralPath 'artifacts/base/qdrant-snapshot.zip' -DestinationPath '.local/base-restored'
Expand-Archive -LiteralPath 'artifacts/advanced/qdrant-v7-snapshot.zip' -DestinationPath '.local/catalog-restored'
$Qdrant = (Resolve-Path '.local/base-restored').Path
$CatalogQdrant = (Resolve-Path '.local/catalog-restored').Path
& $Py -m unittest discover -s tests -v
& $Py -m src.day07 validate --split dev
& $Py -m src.day07 validate --split test
& $Py -m scripts.validate_submission_benchmarks --output .local/benchmark-validation.json
```

Đích giải nén phải chưa tồn tại. Không có writer khác mở cùng Qdrant local. Snapshot đã đối chiếu payload với export; xây lại SQLite từ đầu có thể có hash byte khác dù cùng nội dung.

Định nghĩa hàm chờ server trong cùng phiên PowerShell. Hàm kiểm đúng process vừa tạo, chờ `/health` tối đa 180 giây và báo lỗi nếu process thoát. Dùng cho cả cơ bản và V3.

<!-- server-readiness -->
```powershell
function Wait-LabServer {
    param([int]$ServerProcessId, [int]$ExpectedContext)
    $deadline = (Get-Date).AddSeconds(180)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-Process -Id $ServerProcessId -ErrorAction SilentlyContinue)) {
            throw 'Model server exited. Inspect the .local server logs.'
        }
        $ready = $null
        try { $ready = Invoke-RestMethod 'http://127.0.0.1:8085/health' -TimeoutSec 3 -ErrorAction Stop } catch {}
        if ($ready.status -eq 'ok') {
            $props = Invoke-RestMethod 'http://127.0.0.1:8085/props' -TimeoutSec 5 -ErrorAction Stop
            if ($props.model_alias -ne 'qwen2.5-7b-local' -or
                $props.default_generation_settings.n_ctx -ne $ExpectedContext) {
                throw 'The active model alias or context size differs from the requested server.'
            }
            Write-Output "Server ready: PID $ServerProcessId, context $ExpectedContext"
            return
        }
        Start-Sleep -Seconds 1
    }
    throw 'Model server readiness timed out; inspect the .local server logs.'
}
```

## Cơ bản: dev → review → freeze → test → tổng hợp

Khởi động llama.cpp b12406 bằng lệnh đầy đủ dưới đây: context **4096**, port **8085**, alias `qwen2.5-7b-local`, Vulkan1, GPU layers 99, threads 8, parallel 1 và `--jinja`. Nhiệt độ 0 được runner đặt trong từng request. Đặt binary/DLL của bản Windows Vulkan tại `.local/llama/`; `$TextModel` đã khai báo ở bước chuẩn bị. Kiểm `--list-devices` nếu máy dùng GPU khác; ghi rõ thay đổi phần cứng khi tái lập.

<!-- base-server-start -->
```powershell
$ErrorActionPreference = 'Stop'
$Llama = (Resolve-Path '.local/llama/llama-server.exe').Path
$TextModel = (Resolve-Path -LiteralPath $TextModel).Path
if (Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8085 is occupied. Stop the server you own before starting this stage.'
}
$BaseArguments = @('-m', ('"' + $TextModel + '"'), '--host', '127.0.0.1', '--port', '8085',
    '--alias', 'qwen2.5-7b-local', '--ctx-size', '4096', '--threads', '8', '--parallel', '1',
    '--device', 'Vulkan1', '--n-gpu-layers', '99', '--jinja')
$BaseProcess = Start-Process -FilePath $Llama -ArgumentList $BaseArguments -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput '.local/base-server.out.log' -RedirectStandardError '.local/base-server.err.log'
$BaseServerPid = $BaseProcess.Id
Wait-LabServer -ServerProcessId $BaseServerPid -ExpectedContext 4096
```

Sau khi xuất hiện `Server ready`, chạy dev/test. Dùng `run-id` và đường dẫn output mới; không ghi đè bài đã nộp.

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

Khi hoàn tất cơ bản, dừng đúng process đã tạo và đợi nó thoát trước khi dùng lại port 8085 cho V3. Chạy bước này cả khi chỉ làm phần cơ bản.

<!-- base-server-stop -->
```powershell
$BaseProcess.Refresh()
if (-not $BaseProcess.HasExited) {
    $BaseProcess.Kill()
    $BaseProcess.WaitForExit()
}
```

## Nâng cao hiện tại v3: catalog nguồn → native agent → freeze → test

Xem [thiết kế và giới hạn](CATALOG_V3.md). V3 chỉ cần text model 7B, không cần tải vision weights/projector. 86 câu cũ làm dev; test mới đủ 30 câu và không dùng để chọn cấu hình. Không chạy builder lên benchmark/catalog đã tồn tại. Snapshot giữ byte DB khớp lock; rebuild tạo DB tương đương về nội dung có thể có hash SQLite khác và cần freeze riêng.

Khởi động server text với đúng cấu hình v3: context **16.384**, GPU layers **22**, Vulkan1, threads 8, parallel 1. Helper chạy nền và trả PID do nó tạo. Nếu chạy V3 trực tiếp, vẫn thực hiện phần chuẩn bị và định nghĩa `Wait-LabServer` ở trên; không cần chạy server cơ bản. Nếu vừa chạy cơ bản, thực hiện block dừng server trước.

<!-- catalog-server-start -->
```powershell
$ErrorActionPreference = 'Stop'
if (Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8085 is occupied. Finish and stop the previous server before starting V3.'
}
$CatalogPid = & ./scripts/start_model_server.ps1 -Stage text -ModelPath $TextModel -ConfigPath configs/catalog-v3.json -LogPrefix .local/my-catalog-server
$CatalogProcess = Get-Process -Id $CatalogPid -ErrorAction Stop
Wait-LabServer -ServerProcessId $CatalogPid -ExpectedContext 16384
```

```powershell
$CatalogCommon = @('--day6-root', $Day6Root, '--model-path', $E5Model, '--qdrant', $CatalogQdrant, '--pdf', $Pdf, '--text-model', $TextModel)
# Kiểm lại toàn bộ điểm đã nộp, không gọi model:
& $Py -m scripts.catalog_release score --split dev --traces artifacts/advanced/runs/catalog-a12-dev/traces.jsonl --reviews artifacts/advanced/v3-dev-review.jsonl --output .local/submitted-v3-dev-score.json
& $Py -m scripts.catalog_release score --split test --traces artifacts/advanced/runs/catalog-v3-test/traces.jsonl --reviews artifacts/advanced/v3-test-review.jsonl --output .local/submitted-v3-test-score.json
# Chạy lại đúng release đã khóa, dùng output mới; không thay kết quả test chính thức:
& $Py -m scripts.catalog_release run @CatalogCommon --split test --lock artifacts/advanced/freeze-catalog-v3.json --output artifacts/advanced/runs/my-v3-reproduction
```

Khi phát triển một phiên bản mới, chạy đủ dev và chấm output mới với bản gốc. Các nhãn đã nộp chỉ áp dụng cho đúng SHA trace đã nộp. File annotations chứa verdict, lý do, loại lỗi và audit tất cả alias; script ghép review không tự quyết định đúng/sai.

```powershell
& $Py -m scripts.catalog_release run @CatalogCommon --split dev --output artifacts/advanced/runs/my-v3-dev
& $Py -m scripts.write_source_review --queries benchmarks/advanced-v3/queries/dev.jsonl --gold benchmarks/advanced-v3/gold/dev.jsonl --traces artifacts/advanced/runs/my-v3-dev/traces.jsonl --annotations .local/my-v3-dev-annotations.json --output .local/my-v3-dev-review.jsonl
& $Py -m scripts.catalog_release score --split dev --traces artifacts/advanced/runs/my-v3-dev/traces.jsonl --reviews .local/my-v3-dev-review.jsonl --output .local/my-v3-dev-score.json
& $Py -m scripts.catalog_release freeze @CatalogCommon --dev-run artifacts/advanced/runs/my-v3-dev --reviews .local/my-v3-dev-review.jsonl --output .local/my-v3-freeze.json
& $Py -m scripts.catalog_release run @CatalogCommon --split test --lock .local/my-v3-freeze.json --output artifacts/advanced/runs/my-v3-test
& $Py -m scripts.write_source_review --queries benchmarks/advanced-v3/queries/test.jsonl --gold benchmarks/advanced-v3/gold/test.jsonl --traces artifacts/advanced/runs/my-v3-test/traces.jsonl --annotations .local/my-v3-test-annotations.json --output .local/my-v3-test-review.jsonl
& $Py -m scripts.catalog_release score --split test --traces artifacts/advanced/runs/my-v3-test/traces.jsonl --reviews .local/my-v3-test-review.jsonl --output .local/my-v3-test-score.json
```

Sau khi chạy xong V3 (tái lập test đã nộp hoặc toàn bộ quy trình dev/test), dừng server:

<!-- catalog-server-stop -->
```powershell
$CatalogProcess.Refresh()
if (-not $CatalogProcess.HasExited) {
    $CatalogProcess.Kill()
    $CatalogProcess.WaitForExit()
}
```

Test chạy toàn bộ 30 câu, không có `--limit`; `--dev-ids` bị cấm trên test. Nếu thay phần cứng/runtime, source hoặc code, cần chạy dev và freeze mới; không sửa lock cũ để vượt kiểm hash. Nếu chỉnh từ kết quả test, phải tạo một holdout hoàn toàn mới trước lượt đo chính thức tiếp theo.

Để xây lại catalog nguồn thay vì phục hồi snapshot, dùng đích mới. Builder v7 đọc bản v6 đã nộp; lệnh v6 bên dưới cho phép so nội dung tái tạo độc lập trước đó. Không đưa benchmark vào builder.

```powershell
& $Py -m scripts.build_catalog_v6 --pdf $Pdf --day6-root $Day6Root --model-path $E5Model --output .local/rebuilt-catalog-v6 --qdrant .local/rebuilt-qdrant-v6
& $Py -m scripts.enrich_catalog_v7 --day6-root $Day6Root --model-path $E5Model --output .local/rebuilt-catalog-v7 --qdrant .local/rebuilt-qdrant-v7
```

## Nâng cao v2 lịch sử: dev → review → freeze → toàn bộ test → review → score

Tái lập chính xác v2 tại commit `eec9a4278c5ed1838e3ca3266696f28158db2c51` trong checkout/worktree khác. Fingerprint v2 quét mọi module runtime, vì vậy các module v3 mới ở HEAD làm hash tổng khác dù code v2 được giữ. Core dùng danh sách hash cố định và tiếp tục khớp freeze gốc. Chỉ phần lịch sử v2 cần thêm vision model và projector:

```powershell
$VisionModel = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-q4.gguf').Path
$Projector = (Resolve-Path '.local/downloads/qwen2.5-vl-3b-mmproj-q8.gguf').Path
Expand-Archive -LiteralPath 'artifacts/advanced/qdrant-v5-snapshot.zip' -DestinationPath '.local/advanced-restored'
$AdvancedQdrant = (Resolve-Path '.local/advanced-restored').Path
```

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

```powershell
& $Py -m scripts.audit_catalog_sources --pdf $Pdf --output .local/source-catalog-audit.json
& $Py -m scripts.audit_submission --output .local/submission-audit.json
git diff --check
# Sau khi đã đưa thay đổi được phép vào Git index; server text v3 phải sẵn sàng:
& $Py -m scripts.check_clean_checkout --python $Py --day6-root $Day6Root --model-path $E5Model --pdf $Pdf --text-model $TextModel --checkout .local/new-clean-export --output .local/new-clean-check.json
```

Helper xuất Git index sang một thư mục mới, khôi phục snapshot, chạy unit/validator, chấm lại trace đã nộp, so hash core/catalog/model/PDF/DB và gọi model thật cho **một câu dev**. Smoke mới được lưu cạnh output kiểm tra với hậu tố `-smoke`; không ghi đè smoke đã nộp. Đây là checkout nguồn sạch trên cùng máy, sử dụng dependency và model đã pin đang có sẵn, không phải kiểm chứng trên một máy độc lập.
