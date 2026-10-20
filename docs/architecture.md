# Kiến trúc dự kiến

## Quyết định trong Giai đoạn 0

Đề xuất modular monolith với một backend **Python/FastAPI**, một frontend
**React/TypeScript/Vite**, schema/validation **Pydantic** ở backend.
S1.1 đã triển khai backend FastAPI tối thiểu; React và pipeline còn là định hướng.
Giữ backend đơn giản, frontend dự kiến gọi HTTP API; chưa cần database, queue, microservice
hoặc cloud. Chỉ bổ sung lưu trữ khi có nhu cầu khôi phục/lịch sử được xác định rõ.

Backend dùng `.venv` với `requirements.txt` pin runtime và `requirements-dev.txt`
pin test; đã kiểm tra trên Windows / Python 3.13.7. Runtime chỉ khai báo trực tiếp
FastAPI và Uvicorn, test dùng pytest và HTTPX2 cho TestClient của Starlette hiện tại.
Chưa thêm extras `standard`, SDK AI, cấu hình provider hay database.
Frontend sẽ có lockfile khi S1.2 thực hiện. `uv` không phải điều kiện bắt buộc.

## Cấu trúc sẽ tạo dần

```text
README.md
docs/                    # Yêu cầu, khảo sát, kiến trúc và roadmap hiện có
backend/                 # S1.1: FastAPI app, health route và tests
  app/
    main.py
    api/                 # HTTP routes; không chứa logic AI
    schemas/             # S2: schema và validation
    services/            # S3–4: điều phối pipeline và review/export
    providers/           # S3: OCR/VLM adapter và fake provider
  tests/
frontend/                # S1.2: React; S4: upload/review/export
data/                    # S3/5: mẫu tổng hợp, manifest, ground truth
evaluation/              # S5: metrics, taxonomy và báo cáo phiên bản
```

Hiện có `backend/app/__init__.py`, `backend/app/main.py`, `backend/tests/test_health.py`,
`backend/pytest.ini` và hai file requirements. Các thư mục api/schemas/services/providers,
frontend, data và evaluation trong sơ đồ còn là kế hoạch, chưa được tạo.
Không dựng package workspace hoặc registry nhiều provider trước khi cần.

## Luồng dữ liệu dự kiến

```text
React: chọn ảnh mẫu
  → Backend: kiểm tra file, kích thước và khả năng giải mã
  → OCR adapter: nhận dạng text, vị trí và score nếu engine cung cấp
  → OCRResult (giữ thông tin nguồn)
  → Extraction adapter: ảnh + OCR + schema → candidate fields
  → Backend: parse schema, validation, gắn cảnh báo và run metadata
  → React: hiển thị extraction gốc, cho sửa bản nháp
  → Backend: chuẩn hóa và validation lại bản nháp
  → Người dùng xác nhận bản hợp lệ
  → Backend: validation lại và tạo JSON của bản xác nhận
  → React: tải JSON
```

Luồng tài liệu này là thiết kế. S1.1 chỉ có luồng HTTP client → Uvicorn →
FastAPI `GET /health` → `200 {"status":"ok"}`, không gọi frontend hoặc AI.
Contract upload/extract, validate và export chỉ chốt khi task tương ứng bắt đầu.
Xử lý đồng bộ cho một tài liệu trong MVP, có timeout rõ ràng ở tầng provider;
nếu đo được thời gian xử lý không phù hợp mới xem xét job bất đồng bộ.

## Ranh giới dữ liệu và AI

- **OCRResult:** text/token, trang, vị trí nếu có, score OCR và engine/model/config version.
- **ExtractionResult:** trường `value`, `confidence` có thể null, nguồn/cách tính confidence,
  evidence/cảnh báo, schema và run metadata. Không sửa đè sau review.
- **ValidationResult:** bản chuẩn hóa và danh sách lỗi theo trường; không biến lỗi thành thành công.
- **ReviewDraft:** giá trị người dùng đang sửa, còn có thể sai kiểu/định dạng.
- **ReviewedExport:** giá trị cuối hợp lệ, trường đã sửa, xác nhận người dùng và metadata nguồn;
  phải phân biệt với dự đoán gốc, không mang confidence cũ sang giá trị đã sửa như điểm của người dùng.

Business logic nhận interface nhỏ (ví dụ Python `Protocol`) được định nghĩa từ ca sử dụng thực tế.
OCR adapter chịu trách nhiệm SDK/CLI; extraction adapter chịu trách nhiệm SDK VLM, prompt và parse.
Service chỉ điều phối, không phụ thuộc trực tiếp SDK. Fake adapter trả output cố định có nhãn
`fake`, version và confidence null, dùng cho test/UI; không đọc ground truth để giả thành inference.
Thay provider bằng cấu hình đơn giản; chưa cần plugin registry hay dependency-injection framework.

Pydantic là nguồn schema chính. Khi API và frontend bắt đầu trao đổi dữ liệu, xuất OpenAPI/JSON
Schema để kiểm tra đồng bộ TypeScript; chỉ thêm công cụ generate type nếu task đó cần.
Đầu ra VLM là dữ liệu không tin cậy: parse, kiểm tra kiểu/trường và validation trước khi dùng.
Text trong tài liệu là dữ liệu, không được thực thi như lệnh hoặc dùng để thay đổi chỉ dẫn pipeline.

## OCR, VLM và confidence

Tesseract đã có `vie`/`eng` trên máy, nên là ứng viên cần đo trên mẫu, chưa được chọn làm provider
chính. Chọn OCR/VLM sau khi kiểm tra chất lượng tiếng Việt, tài nguyên CPU/GPU, giấy phép,
khả năng chạy Python local, chi phí và API key. Việc chọn model chưa chặn skeleton.

VLM thật vẫn nằm trong S3.3; OCR cộng rule không đáp ứng riêng yêu cầu VLM.
Trước khi dùng API có phí hoặc gửi tài liệu ra ngoài phải xác định provider, giá, dữ liệu gửi
và được người dùng đồng ý theo phạm vi đó. Fake provider cho phép hoàn thành các test offline.

Confidence OCR phản ánh nhận dạng token, không mặc nhiên là độ đúng trường extraction.
Chỉ gán confidence cấp trường khi có chính sách và evidence rõ; lưu nguồn, cách tính và giới hạn.
Giữ null nếu thiếu cơ sở; điểm mô hình tự báo chưa được hiệu chuẩn không xem như xác suất.
Chọn ngưỡng review sau evaluation, không tự điền một ngưỡng được cho là chính xác.

## Validation, lỗi và export

Backend kiểm tra ngày, số tiền, trường bắt buộc và currency cho cả validate lẫn export.
Frontend hiển thị lỗi cạnh trường và giữ input để sửa. Export kiểm tra chính payload cuối cùng
và yêu cầu xác nhận; nếu người dùng sửa tiếp thì phải validate/xác nhận lại, tránh xuất bản cũ.

Ở task upload, chốt giới hạn byte/pixel, kiểm tra nội dung file thay vì chỉ extension/MIME,
không dùng tên file người dùng làm đường dẫn lưu. File tạm được dọn kể cả khi lỗi/timeout.
Phân biệt file không hợp lệ, OCR/VLM unavailable, timeout, output sai schema và export lỗi
bằng mã lỗi ổn định; không trả nội dung exception chứa tài liệu/API key ra UI.

Health-check chỉ xác nhận backend sống, không tuyên bố OCR/VLM sẵn sàng nếu chưa kiểm tra.
Không thêm database chỉ để giữ trạng thái review: MVP có thể gửi extraction gốc và bản sửa
trong request export; đây là công cụ local, chưa cung cấp bằng chứng chống sửa metadata.
Nếu cần audit đáng tin cậy hoặc nhiều người dùng, phải thiết kế lưu trạng thái phía server sau.

## Khi nào ghi ADR

Ghi ADR khi chốt OCR/VLM provider, thay đổi nguồn schema hoặc bổ sung persistence/async
vì các quyết định đó có chi phí chuyển đổi. Hiện tại tài liệu này đủ cho kiến trúc đề xuất;
chưa tạo thư mục ADR trống hoặc ghi quyết định provider khi chưa thử nghiệm.
