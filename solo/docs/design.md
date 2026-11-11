# Phạm vi, kiến trúc và kế hoạch bản cá nhân

## Quyết định ban đầu — 2026-11-11

- Giữ nguyên ứng dụng cũ, nhánh main chung và lịch sử Git.
- Xây mã ứng dụng độc lập trong `solo/`, trên nhánh `personal/canhtung-solo`.
- Một người quản lý toàn bộ module; ghi nhận trợ giúp AI, không đổi tác giả
  các commit cũ hoặc tuyên bố tự huấn luyện Tesseract/VLM.
- Python/FastAPI/Pydantic, React/TypeScript/Vite, Tesseract `vie+eng`.
- VLM qua API Ollama local, ảnh thật + OCR context + JSON Schema. Không trả
  fixture giả khi engine/model chưa sẵn sàng; không tự chuyển sang chế độ khác.
- Không cần database, authentication, cloud deployment hoặc dữ liệu cá nhân.

## Thư mục và ranh giới

| Đường dẫn | Vai trò |
| --- | --- |
| `backend/src/ai02_solo/` | Contract, registry schema, preprocessing/OCR, extraction, API |
| `backend/tests/` | Logic validation, evidence, adapter và HTTP |
| `web/` | React upload/preview/review/JSON, chỉ gọi HTTP |
| `data/` | Generator, tài liệu synthetic, ground truth, manifest hash và split |
| `evaluation/` | Baseline/report được tuyển chọn; report runtime bị ignore |
| `docs/` | Quyết định kỹ thuật, demo, lỗi và bằng chứng kiểm thử |

Registry Pydantic là nguồn schema. Backend cung cấp registry và JSON Schema cho
UI; validation và export đều chạy phía server để tránh duy trì luật ở hai nơi.
Evaluation gọi cùng hàm pipeline như API. Không import package implementation cũ.

## Hai schema MVP

Hóa đơn: `invoice_number`, `invoice_date`, `seller_name`, `total_amount`,
`currency` (VND). Đơn đề nghị: `applicant_name`, `student_id`, `recipient`,
`request`, `submission_date`. Mọi danh tính trong fixture là giả và có nhãn.
Ngày ISO, tiền integer không âm; missing/invalid/ambiguous là null. Người dùng
chọn loại tài liệu thay vì tự phân loại ngầm. Chưa hỗ trợ viết tay/nhiều trang.

Confidence là tín hiệu heuristic với nguồn rõ ràng, không phải xác suất đã hiệu
chuẩn. Với giá trị VLM không được OCR chứng thực, confidence null và cảnh báo.
Không dùng con số confidence do mô hình tự khai. Hybrid chỉ kết hợp kết quả có
bằng chứng; khi hai nguồn bất đồng, giữ null cho người dùng quyết định.

## Checkpoint và acceptance

1. Contract: hai schema, normalization, validation theo trường và export giữ
   nguyên extraction gốc; tests ngày, tiền, thiếu trường, key/kiểu sai.
2. OCR/extraction: decode PNG/JPEG/PDF một trang có giới hạn, Tesseract thật,
   baseline nhiều kiểu nhãn, adapter VLM JSON có version/digest/prompt hash;
   tests không dùng response giả làm bằng chứng model thật.
3. HTTP/UI: chọn schema/chế độ, upload, preview, confidence/evidence, sửa và
   validation; chỉ export snapshot hiện tại, request cũ không ghi đè tài liệu mới.
4. Evaluation: dataset synthetic độc lập, frozen split trước chạy, hash file/
   truth, exact match/PRF từng trường, taxonomy, config/model/code version.
5. Verification: kiểm tra thật PNG/JPEG/PDF, review→JSON, trường thiếu và lỗi;
   chạy CI, ghi rõ phần chưa kiểm chứng, hướng dẫn demo, push nhánh cá nhân.

Commit nhỏ theo Conventional Commits, stage từng path, xem staged diff trước
commit. Người dùng đã yêu cầu push bản cá nhân; không tự merge main/force push.

## Tài liệu adapter VLM

- [Ollama vision](https://docs.ollama.com/capabilities/vision): REST nhận ảnh base64.
- [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs):
  gửi JSON Schema trong `format`, vẫn validate lại kết quả bằng Pydantic.
- [Model metadata](https://docs.ollama.com/api/tags): ghi digest thực tế, không
  chỉ lưu tag có thể thay đổi.
- [Qwen3-VL 2B](https://ollama.com/library/qwen3-vl:2b): ứng viên nhỏ để đo
  trên M1 8 GB; chưa tuyên bố tốc độ hoặc độ chính xác khi chưa chạy model.
