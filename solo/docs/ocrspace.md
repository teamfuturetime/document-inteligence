# OCR.space — tích hợp và thử nghiệm

Adapter dựa trên [tài liệu chính thức OCR.space](https://ocr.space/ocrapi),
đọc ngày 2026-11-11. Đã gọi API thật bằng tài liệu synthetic; không dùng dữ liệu
cá nhân. Đây là nguồn **OCR**, vẫn dùng schema/rules và review của ứng dụng;
không thay thế phần model VLM đang để cấu hình sau.

## Dùng ngay trên giao diện

1. Chạy backend/web như README, mở http://127.0.0.1:5174 và tải lại trang.
2. Chọn **Nguồn OCR → OCR.space (API)**, **Phương pháp → OCR + luật**.
3. Chọn đúng loại tài liệu, upload một file trong `data/golden-v1/`.
4. Rà soát, sửa nếu cần, kiểm tra dữ liệu rồi xuất JSON.

API key hiện được cấu hình ở backend trong `solo/.secrets/ocrspace.key`, file
mode 0600, thư mục mode 0700, Git ignore. Trình duyệt chỉ gửi `ocr_provider`,
không nhận hoặc gửi API key. `/health` chỉ kiểm tra có cấu hình, không gọi API,
không chứng minh quota còn hoặc key luôn hợp lệ. Extraction mới kiểm tra thực tế.

Trên máy khác, cung cấp `SOLO_OCRSPACE_API_KEY` trong môi trường backend hoặc
tạo cùng file private. Env được ưu tiên trước file; không đặt key trong biến
`VITE_*`, mã frontend, URL hoặc GitHub repository. Có thể đổi đường dẫn file
bằng `SOLO_OCRSPACE_KEY_FILE`. Không cần Tesseract khi chọn OCR.space.

Backend mặc định Tesseract. Nếu muốn khởi tạo UI mặc định là OCR.space:

```bash
# Chạy từ solo/, sau khi đã cấu hình key riêng:
SOLO_OCR_PROVIDER=ocrspace uv run --locked uvicorn ai02_solo.api:app --host 127.0.0.1 --port 8100
```

## Request và response

- Endpoint cố định HTTPS `POST https://api.ocr.space/parse/image`.
- API key trong header `apikey`, upload file multipart PNG sau preprocessing.
- `OCREngine=2`, `language=auto`, `isOverlayRequired=true`, `isTable=true`,
  `scale=false`, `detectOrientation=false`, không tạo searchable PDF.
- Tài liệu OCR.space dùng `vnm` cho mã tiếng Việt legacy, khác `vie` của
  Tesseract. Engine 2/3 khuyến nghị auto-detection nên adapter dùng `auto`.
- Có thể đặt `SOLO_OCRSPACE_ENGINE=3`; lần thử hiện tại chỉ kiểm chứng Engine 2.
- App vẫn nhận PNG/JPEG/PDF một trang; JPEG/PDF được decode/render thành PNG.
  Chặn PNG **sau tiền xử lý** lớn hơn 1.000.000 bytes để phù hợp Free tier 1 MB,
  không tự giảm độ phân giải/chất lượng hoặc chuyển sang engine khác.
- Chỉ nhận success đầy đủ, một page, overlay hợp lệ. Không dùng partial result
  hoặc bịa tọa độ khi thiếu overlay; lỗi/quota/timeout trả thông báo an toàn.
- Mỗi lượt upload gọi API một lần, không retry tự động. Không theo redirect
  mang header key; response giới hạn 4 MiB, request timeout 60s và nằm trong
  deadline worker của pipeline.

`TextOverlay.Lines[].Words[]` được chuyển thành Token với text/box/dòng thật.
Response được mô tả và nhận trong lần thử không có confidence theo từ; adapter
luôn đặt confidence null, UI báo rõ. Không suy ra điểm 100% từ success/exit code.
Khi xuất JSON, confidence vẫn null trong original extraction; sửa tay lưu riêng.

Provenance ghi provider, engine, adapter version, parameters/config hash và
`version_source=service_managed_unpinned`, `model_revision=null`. Nhà cung cấp
không công bố revision trọng số trong response, nên không tuyên bố cloud có
model hash đã pin hoặc cho kết quả byte-identical ở mọi thời điểm.

## Kết quả thử và kiểm tra

Đã thực hiện bốn request cloud trên ba mẫu dev synthetic:

| Mẫu | Kiểm tra thực tế |
| --- | --- |
| `invoice-001.png` | API trả overlay; luồng UI đọc đúng 5 trường, sửa bên bán, tải JSON |
| `invoice-002.jpg` | Pipeline cloud đọc đúng 5 trường, gồm tiếng Việt, ngày và tiền |
| `application-003.pdf` | Đọc đúng các trường hiện diện, giữ request bị thiếu là null |

Đây là smoke test nhỏ, chưa phải kết quả benchmark OCR.space trên golden test.
Các report/baseline rules v1/v2 đã commit trước đó là **Tesseract**; không đổi
tên hoặc sử dụng các điểm đó để quảng cáo chất lượng OCR.space.

63 Python tests đạt, gồm mock transport/parser/cloud errors và real Tesseract;
7 UI tests/typecheck/build đạt, 7 E2E Tesseract đạt. Live browser cloud đã xác
nhận provider OCR.space, 5/5 giá trị đúng, confidence null, JSON giữ original và
edited_fields, key không nằm trong request trình duyệt. Đã xem desktop/mobile
390px không tràn ngang. Các output runtime nằm trong `evaluation/reports/` và
`web/test-results/` (ignored), không chứa API key.

Có smoke script tái lập, chỉ chạy khi bật opt-in và sẽ dùng **một** lượt API:

```bash
# Backend/web đã chạy; từ solo/web:
SOLO_RUN_OCRSPACE=1 npm run test:ocrspace
# Nếu dùng Chrome đã cài thay Chromium của Playwright:
SOLO_RUN_OCRSPACE=1 SOLO_BROWSER_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:ocrspace
```

Unit/CI thông thường không gọi OCR.space hoặc cần key thật. Khi muốn đo đầy đủ
trên dev (18 request cloud, không phải smoke), chủ động chạy:

```bash
# Từ solo/; chỉ chạy khi muốn sử dụng quota API:
uv run --locked python -m ai02_solo.evaluate --ocr-provider ocrspace --mode rules --split dev --output evaluation/reports/dev-ocrspace.json
```

Lệnh tương tự với `--ocr-provider tesseract` cho so sánh trên cùng manifest.
Không bỏ dấu khi chấm để che lỗi; chọn provider/config từ dev trước đánh giá test.
