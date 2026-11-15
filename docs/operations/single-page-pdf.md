# Tải và kiểm tra PDF một trang

Chọn PDF synthetic/sample có quyền sử dụng, đúng một trang, trong workspace. Server nhận bytes gốc và kiểm nội dung. PDF được render local thành ảnh xám trên nền trắng ở 200 DPI, rồi chạy Tesseract như ảnh PNG/JPEG. Vùng OCR được đặt trên chính frame PNG trả cho trình duyệt. PDF gốc và SHA-256 được giữ nội bộ để chạy lại và truy vết.

`GET /api/v1/capabilities` trả `upload_media_types` gồm `image/png`, `image/jpeg`, `application/pdf`. `POST /api/v1/documents` nhận body raw với query `document_type`, `data_origin`, `filename` và tùy chọn `Idempotency-Key`. Ví dụ PowerShell:

```powershell
$sample = 'pipeline/tests/fixtures/pdf/hoa_don_007.pdf'
$url = 'http://127.0.0.1:8000/api/v1/documents?document_type=hoa_don&data_origin=synthetic&filename=hoa_don_007.pdf'
Invoke-RestMethod $url -Method Post -InFile $sample -ContentType 'application/pdf' -Headers @{'Idempotency-Key'='demo-pdf-007'}
```

| Giới hạn | Mặc định |
| --- | --- |
| Body, nhận dữ liệu, upload đồng thời | 5 MiB, 30 giây tổng, 2 upload như [ingress hiện hành](upload-ingress.md) |
| Raster PDF | 8192 pixel mỗi chiều, tối đa 16 triệu pixel qua `DOCINTEL_MAX_IMAGE_PIXELS` |
| Preview và pipeline | Preview tối đa 5 giây hoặc timeout pipeline nếu nhỏ hơn; OCR dùng deadline pipeline mặc định 30 giây |

PDF hỏng/truncated, có mã hóa (kể cả empty password) hoặc nhiều trang trả 415 với `INVALID_PDF`, `PDF_ENCRYPTED` hoặc `PDF_PAGE_COUNT`. Request content encoding khác identity trả 415 `UNSUPPORTED_CONTENT_ENCODING`. PDF vượt cap bytes hoặc kích thước trả 413. Preview vượt deadline trả 408 `PROCESSING_TIMEOUT`. Retry chọn đúng file/loại/nguồn để dùng lại cùng khóa. Khi OCR đã vào queue nhưng lỗi, thông tin nằm trong run.

Dữ liệu nghiệm thu lấy từ [fixtures synthetic](../../pipeline/tests/fixtures/pdf/README.md). Chạy:

```powershell
uv run --project backend --locked pytest pipeline/tests/test_pdf.py backend/tests/test_pdf_upload.py -q
uv run --project backend --locked python scripts/verify_product.py
npm --prefix frontend run test:e2e
```

Native kiểm OCR thật với PNG, PDF và đơn đề nghị, JPEG được kiểm ở pipeline. Browser chạy riêng luồng PNG và PDF đến JSON tải về. Mẫu là scan đóng gói từ ảnh synthetic và không dùng để ước lượng chất lượng OCR tổng quát. PDF nhiều trang, form tương tác, chữ viết tay và triển khai công khai nằm ngoài phạm vi. Parser chạy trong subprocess có deadline và cap bitmap, không có giới hạn RSS cứng. Bộ render pin qua lock và dùng [license notices của wheel PDFium](https://pypdfium2-team.github.io/pypdfium2/readme.html#licensing).
