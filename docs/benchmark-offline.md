# S3.3.2a — Benchmark runner và parser/evidence adapter offline

Ngày kiểm tra: 21/10/2026. **Fixture simulation, không phải benchmark chất lượng VLM**.
Không tải/chạy VLM, gọi API, thêm dependency hoặc thay S3.1/S3.2/schema sales_invoice 1.0.0.

## Phạm vi so với khảo sát

[Khảo sát S3.3.1](vlm-survey.md) đề xuất runner kèm inference thật và resource guard.
Prompt S3.3.2a hiện tại tách phần đó sang **S3.3.2b**: lượt này chỉ hiện thực contract,
parser, source lookup, metrics và báo cáo bằng fixture. Chưa có model loader, deadline
VLM, giới hạn RAM cho inference hoặc kết quả quality/latency của model.
Các thay đổi khảo sát có sẵn được giữ, không stage/commit/push.

## Chạy local

Sau khi có môi trường backend theo README, chạy từ thư mục gốc:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.benchmark
..\.venv\Scripts\python.exe -m app.benchmark --without-labels
..\.venv\Scripts\python.exe -m app.benchmark --measure
Pop-Location
```

CLI chỉ ghi report JSON UTF-8 ra stdout; fixture không hợp lệ trả exit 1 và code
`invalid_benchmark_fixture`. Không tạo export API/file hoặc chạy OCR/model. Có thể
truyền `--manifest`, `--sources`, `--responses`, `--labels`, `--code-revision`.
Code revision mặc định null, không tự bịa Git/model revision.

Không `--measure`: không đọc clock, elapsed_seconds null, output xác định cho cùng
input/config/fixture/labels. `--measure` dùng perf_counter đo thời gian dựng request,
fixture response, parse và evaluate; **không phải VLM latency**, không bao gồm tổng hợp
toàn báo cáo. Run ID ổn định là hash metadata/request/response, không phải UUID lần gọi.

## Input/output contract

`backend/app/benchmark/contracts.py` định nghĩa BenchmarkProvider có identity và
`respond(BenchmarkRequest) -> str`. Identity có ProviderIdentity hiện có cùng model ID
và revision nullable. Runner S3.3.2a chỉ cho mode fake và model ID/revision null;
provider mode real bị từ chối trước respond. Không sửa ExtractionProvider hoặc gọi
run_pipeline hiện có; benchmark là công cụ độc lập.

| Mode | Provider nhận | Provider không nhận |
| --- | --- | --- |
| image-only | sample ID, ảnh DocumentInput, source locale đã biết | OCR context, labels, manifest expected_text hoặc đường dẫn label |
| ocr-text-only | sample ID, OCRContext, source locale | bytes ảnh, labels hoặc expected_text |
| image+ocr | ảnh và OCRContext khớp sample ID/input hash, source locale | labels hoặc expected_text |

OCRContext chứa text/hash, origin/provenance, kích thước ảnh hiển thị và SourceSpan:
ID, start/end theo **Unicode code point**, page 1, bbox/native score nullable. Kiểm tra
text hash, ID duy nhất, offsets, bbox trong kích thước nguồn và liên kết ảnh/manifest.
Các field input không mang ground truth; provider nhận bản sao sâu. Đây là tách
trách nhiệm ở code, không phải sandbox ngăn một Python provider độc hại đọc filesystem.

Response JSON là object chỉ có các key sau:

- `raw_values`: đủ đúng năm key hóa đơn; string/null, riêng total_amount thêm integer.
  Null khác missing key. Không nhận bool/float như tiền, integer như invoice number.
- `evidence`: map tên field → danh sách SourceSpan IDs, có thể bỏ key/mảng rỗng khi
  không có nguồn. Không nhận tọa độ/quote model tự tạo làm evidence.
- `uncertain_fields`: danh sách field, mặc định rỗng.
- `model_reported_scores`: map field → số hữu hạn hoặc null, mặc định rỗng. Chỉ giữ
  như dữ liệu model tự báo, thang đo chưa xác minh; không đổi sang confidence extraction.

Parser nhận JSON trần hoặc một markdown fence bao toàn bộ response, nhãn json/JSON
hoặc không nhãn. Từ chối prose trước/sau, nhiều fence, duplicate JSON keys, NaN,
Infinity/overflow, Unicode surrogate lỗi, root sai kiểu, key lạ và wrong types.
Không sửa dấu nháy, cắt prose để tìm JSON, tự điền key hoặc đoán giá trị. Response
trên một triệu ký tự bị parse_error. Raw response UTF-8/hash giữ trong report; chuỗi
không thể biểu diễn UTF-8 giữ parse error và raw/hash null, không làm CLI crash.

Status mỗi run: `processed`, `parse_error`, `schema_error`, `provider_error` hoặc
`input_error`. Lỗi có field/code/message; message không lấy từ exception provider.
Processed chỉ là đã xử lý response, không có nghĩa hóa đơn hợp lệ/đã được người dùng duyệt.

## Evidence và hai lớp validation

Adapter tìm ID trong nguồn request; text được cắt từ nguồn bằng offsets. Bbox nếu có
được copy từ source đã cung cấp, không nội suy/tự tạo; bbox thiếu vẫn null. ID lạ,
trùng, không đúng thứ tự/liền đoạn, claim cho null hoặc không hỗ trợ giá trị field
trả lỗi evidence theo field. Cùng quote/ID hợp lệ vẫn chưa chứng minh chọn đúng nhãn
trên ảnh; provenance của OCR snapshot phải được bên tạo nguồn kiểm chứng.

So sánh nguồn/giá trị dùng lại normalization + validation S2.2, không thêm rule ngày,
tiền hoặc currency. Giữ nguyên raw_values. Report tách:

- `candidate_validation`: diagnostic trên raw values trước evidence/uncertainty gate.
- `accepted_validation`: field thiếu/sai evidence hoặc model uncertain bị chặn null,
  có lỗi giải thích. Kể cả currency suy ra từ hậu tố tiền qua S2.2 vẫn cần evidence
  riêng trước khi chấp nhận. Không thay đổi quy tắc S2.2.

`ProviderOutput` trong report dùng cấu trúc S3.1 nhưng là kết quả adapter benchmark,
không đưa vào pipeline fake S3.1 (pipeline đó cố ý cấm fake claim OCR/evidence).
Không tạo ExtractionResult đầy đủ hay trạng thái review/export.

`FieldMetadata.confidence` luôn null. OCR-native score nằm trong OCRContext span,
model-reported score ở key riêng, metrics ở phần diagnostic. Không lấy trung bình,
chia 100 hay gán chúng thành xác suất đúng; không tạo calibration version.

## Dataset và fixture

- Dùng nguyên ba ảnh/hash/manifest `data/ocr-smoke/`: hai định dạng của cùng một
  hóa đơn tổng hợp và một blank, không phải ba invoice độc lập.
- `data/benchmark-fixture/source-text.txt`, `ocr-inputs.json`: nguồn text tổng hợp
  viết sẵn, spans lấy từ chuỗi; origin synthetic_text_fixture, **không phải OCR đo được**.
  Tất cả bbox/native score null; contract từ chối gắn số đo/toạ độ vào origin này.
- `responses.json`: câu trả lời viết sẵn, có fenced JSON; tên/version fixture rõ ràng.
  Không suy luận từ ảnh, không dùng model, model-reported scores mặc định rỗng.
- `labels.json`: canonical labels riêng, chỉ evaluator đọc. Loader không đưa
  manifest expected_text vào request. Fixture response đương nhiên là đáp án viết
  sẵn để test plumbing; không dùng kết quả để suy ra chất lượng model.

Fixture text/response/labels là nội dung tổng hợp gốc của dự án, dành theo CC0-1.0;
không có dữ liệu cá nhân hoặc model/font mới. Thiếu annotation được biểu diễn bằng
ground_truth=None, khác object đủ năm key null của negative có annotation.

## Metric và mẫu số

- Exact: cùng kiểu và cùng giá trị raw/canonical label, giữ số 0 đầu/case/dấu. Raw
  `125.000` string khác integer 125000 và DMY khác ngày ISO.
- Normalized: dùng giá trị từ S2.2 với locale nguồn; không đoán format mơ hồ. Accepted
  match so thêm kết quả sau evidence gate. Cả ba ghi theo field và từng run/mode.
- Non-null totals chỉ gồm field label khác null nhưng **giữ mọi run đã lên lịch**;
  parse/schema/provider/input failure tính sai, không biến mất khỏi mẫu số.
- Null/null được báo riêng, không tăng non-null accuracy. Prediction invalid bị
  validation đổi thành null không được tính abstention đúng. False positive tính
  field có raw value không rỗng hoặc có giá trị normalized khác null; parse/schema
  failure là unknown, không phải negative pass.
- `null_false_positive_rate_observed` chỉ chia số quan sát được; kèm null_unknown và
  `null_pass_rate_planned` trên mọi negative slot để không che failure. Không có GT
  hoặc mẫu số 0 → metric null/N/A, không phải 0% hay 100%.
- Evidence coverage dùng normalized candidates quan sát được làm mẫu số, độc lập
  annotation; kèm evidence error theo field/code. Không gộp coverage vào accuracy/confidence.
- Report có overall và by_mode, positive all-five-correct/negative all-null riêng,
  lỗi parse/schema/evidence và candidate/accepted errors. Không có PRF/calibration/p95.

Report luôn có `result_kind=fixture_simulation`, `is_model_quality_benchmark=false`,
`inference_performed=false`. Metadata ghi runner/parser/metrics/schema/normalization
versions, provider implementation/config version, model ID/revision null, dataset
manifest/label/source/response hashes, mode và code revision nếu bên gọi cung cấp.
Mỗi record giữ input/request/response hash, source provenance, status/errors và timing
nếu đo. Không đưa key model/config bịa để khiến fixture giống inference thật.

Ví dụ kiểm đếm bằng tay cho fixture mặc định (không phải số đo model): 9 run, 6 positive
và 3 negative; 30 non-null field slots. Total amount exact 0/6 do raw string, normalized
6/6, accepted 4/6 vì hai run image-only không có OCR evidence. Negative all-null 3/3.
Những con số này chỉ kiểm tra công thức/report của fixture đã biết.

## Kiểm thử thực tế

Baseline trước sửa code: 463 passed in 2.93s. Sau triển khai:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests/test_benchmark.py -q
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
git diff --check
git diff --cached --check
```

Nhóm benchmark: **68 passed in 1.12s**. Toàn suite đã chạy: **531 passed in 3.60s**, gồm 463 test cũ + 68 test mới, không warning/skip.
Test benchmark chặn network và OCR recognize trong tiến trình; CLI test chỉ chạy lại
Python fixture runner. Full suite vẫn chạy các test Tesseract thật có sẵn của S3.2,
không có VLM inference. Chưa cấu hình type checker/linter backend.

Test mới gồm fences/JSON/duplicate/nonfinite/Unicode/schema; source ID/offset/hash/
bbox/null/uncertainty; raw vs normalized/zero/leading zero/no GT/planned denominator;
model score không trở thành confidence; input projection không label, không sửa nguồn,
deterministic report, optional fixture timing, provider failure sanitization và CLI.
Lần đầu test spy dùng model_fields qua instance tạo deprecation warning (config coi
warning là lỗi); đã đổi sang class, giữ nguyên cấu hình strict warnings.

## S3.3.2b — chưa triển khai

Sau khi được giao task và chấp thuận runtime/model: pin weights/mmproj/runtime/license,
thêm provider inference thật và timeout/resource guard, dùng cùng request projection,
parser và metric. Chuẩn bị OCR snapshot thật có provenance để thay text fixture;
thêm source mapping từ ảnh/crop chỉ khi đã kiểm chứng, không chế evidence image-only.
Chạy tối thiểu một inference ảnh và 9 run ban đầu (hoặc báo chính xác lỗi/không hỗ trợ),
ghi resolved model version/usage/memory/time thật và không tự sửa lỗi output để tăng điểm.
Chưa có bằng chứng quality/latency/VRAM; không tích hợp API/UI/export ở bước offline này.
