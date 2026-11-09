# Hỗ trợ định dạng ảnh upload

Triển khai trên branch `bt3-vt043-autosave`. Hỗ trợ PDF, PNG, JPG, JPEG, WebP, BMP, TIF và TIFF. GIF, HEIC và HEIF bị từ chối.

## Hành vi

- Upload: chọn file hoặc kéo thả; kiểm tra extension và MIME tương ứng, giữ giới hạn 10 MB. MIME rỗng hoặc `application/octet-stream` được xử lý bằng chữ ký và giải mã thực tế; backend lưu MIME chuẩn trong trường hợp này.
- Backend: kiểm tra chữ ký, dùng Pillow kiểm tra và giải mã từng trang trước khi ghi metadata. File rỗng, sai định dạng, hỏng, vượt giới hạn sẽ bị từ chối và file tạm được dọn. PNG còn được kiểm tra CRC của các chunk dữ liệu.
- OCR: tái sử dụng deskew và các bước preprocessing hiện có. Đọc TIFF theo thứ tự trang, lần lượt đưa từng trang vào OCR; giữ cấu trúc `ocr.pages`, số trang, word boxes, extraction và dấu phân trang trong raw text. Áp dụng orientation, ghép alpha trên nền trắng và chuyển grayscale 16-bit về 8-bit có tỷ lệ để tránh mất tông ảnh.
- Preview: PDF, PNG, JPEG và WebP giữ URL/cách hiển thị hiện có. BMP/TIFF được backend chuyển thành PNG theo yêu cầu `GET /api/v1/documents/{id}/preview?page=1`, trả `X-Page-Count`. Frontend có chuyển trang và trạng thái tải/lỗi; thu hồi Blob URL khi đổi trang/rời trang. Chỉ ảnh preview được thu nhỏ tối đa 2400 × 2400; file gốc và ảnh đầu vào OCR giữ nguyên.
- Mọi thao tác tiếp tục dùng authentication, CSRF và kiểm tra ownership hiện có. Không thay schema, API field, raw OCR hay logic lưu bản hiệu chỉnh; không thêm migration.

Pillow hỗ trợ truy cập các trang TIFF bằng `seek()`; tham khảo [tài liệu TIFF chính thức](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#reading-multi-frame-tiff-images).

## Giới hạn mặc định

| Tham số | Giá trị |
| --- | --- |
| `MAX_UPLOAD_SIZE_MB` | 10 MB |
| `MAX_IMAGE_PIXELS` | 40.000.000 pixel/trang |
| `MAX_IMAGE_PAGES` | 20 trang TIFF |
| `MAX_TOTAL_IMAGE_PIXELS` | 80.000.000 pixel/tài liệu ảnh |
| `MAX_PDF_PAGES` | 20 trang PDF, giữ cơ chế hiện có |

Kiểm tra kích thước và tổng pixel trước khi giải mã. Không dùng `n_frames` để quét không giới hạn chuỗi trang TIFF, và không giữ toàn bộ ảnh TIFF đã giải mã trong bộ nhớ cùng lúc. Backend và AI service nhận cùng giới hạn ảnh trong Docker Compose. Nếu dùng `.env` riêng, cập nhật `ALLOWED_EXTENSIONS` theo `.env.example`; parser hỗ trợ cả JSON list và CSV. `.env` cục bộ trong workspace đã được cập nhật riêng dòng extension, không đưa vào Git.

## File đã thay đổi

| Nhóm | File |
| --- | --- |
| Bộ giải mã dùng chung | `document_images.py` (mới) |
| Backend | `backend/app/core/config.py`, `backend/app/services/file_validation.py`, `backend/app/services/upload.py`, `backend/app/services/preview.py` (mới), `backend/app/api/documents.py`, `backend/requirements.txt` |
| AI/OCR | `ai_service/config.py`, `ai_service/validation.py`, `ai_service/main.py`, `ai_service/pipeline.py` |
| Frontend | `frontend/src/utils/files.ts`, `frontend/src/pages/UploadPage.tsx`, `frontend/src/pages/DocumentDetailPage.tsx`, `frontend/src/components/DocumentPreview.tsx` (mới) |
| Python test | `tests/conftest.py`, `tests/unit/test_file_validation.py`, `tests/unit/test_image_formats.py` (mới), `tests/unit/test_ai_api.py`, `tests/unit/test_backend_api.py`, `tests/integration/test_document_review.py` |
| Frontend test | `frontend/src/utils/files.test.ts`, `frontend/src/components/DocumentPreview.test.tsx` (mới), `frontend/src/pages/UploadPage.test.tsx` (mới) |
| Docker/cấu hình | `backend/Dockerfile`, `ai_service/Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example` |
| Kiểm chứng và tài liệu | `scripts/verify_image_formats.py` (mới), `README.md`, `docs/demo-guide.md`, `docs/upload-image-formats.md` (mới) |

Hai file chưa được Git theo dõi có sẵn (`ocr-review.patch` và file tên bắt đầu bằng `how 75a0feb`) không bị chỉnh sửa. Không commit, push hoặc merge.

## Dependency

Backend bổ sung `Pillow==11.0.0` để giải mã xác thực và tạo preview. Đây là thư viện/phiên bản đã dùng trong AI service; không thêm thư viện frontend hay OCR mới. `document_images.py` được copy vào cả hai image Docker để dùng chung quy tắc giải mã.

Khi chạy backend ngoài Docker, khởi động từ gốc repository bằng `python -m uvicorn app.main:app --app-dir backend --reload --port 8000` để import được bộ giải mã dùng chung; hướng dẫn demo đã được cập nhật.

## Kết quả kiểm thử

| Kiểm tra | Kết quả |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q -rs` | 241 PASS, 1 SKIP; không FAIL |
| `npm.cmd test` (frontend) | 78 PASS / 9 file; không FAIL |
| `npm.cmd run build` | PASS |
| `npm.cmd run typecheck` | PASS |
| `npm.cmd run lint` | PASS |
| Script OCR thật trong AI container | 8/8 PASS: WebP, BMP, TIF, TIFF hai trang, PNG, JPG, JPEG, PDF hai trang |
| Script API với AI service thật | 8/8 PASS: upload → OCR → preview → sửa OCR/extraction → confirm → export → reopen → delete |

Test SKIP có sẵn: `tests/unit/test_storage.py` không tạo được symlink trên môi trường Windows hiện tại. Các dependency có cảnh báo deprecation từ Starlette/PyMuPDF; fixture TIFF hỏng phát cảnh báo EXIF trước khi được từ chối đúng. Không có test thất bại còn lại.

Các test mới kiểm tra file thật, MIME/extension giả mạo, ảnh hỏng, CRC PNG sai, rỗng, vượt 10 MB, decompression bomb, giới hạn trang/pixel/tổng pixel và trang TIFF sau bị hỏng. Kiểm tra thêm transparency, orientation PNG/JPEG/TIFF, grayscale 16-bit và TIFF raw/LZW/Deflate/PackBits. Test API xác minh file gốc không đổi và file không hợp lệ không để lại bản ghi/file.

Regression đã chạy: PDF/JPG/JPEG/PNG, cấu trúc OCR/extraction, preview, lưu OCR giữ raw text, autosave/revision, review/confirm/reopen/export, xóa, authentication, CSRF và ownership. Integration test thường giả lập bước nhận dạng để kiểm tra hợp đồng dữ liệu; hai chế độ script bên dưới chạy Tesseract thật. Chế độ API dùng SQLite và thư mục tạm riêng, gọi AI service qua HTTP; không ghi vào PostgreSQL đang dùng.

Chạy lại kiểm chứng Docker bằng PowerShell từ thư mục gốc:

```powershell
docker compose up -d --build
Get-Content -Raw scripts/verify_image_formats.py | docker compose exec -T ai_service python -
Get-Content -Raw scripts/verify_image_formats.py | docker compose exec -T backend python - --api
```

## Kiểm tra qua giao diện

1. Mở `http://localhost:3000`, đăng nhập và vào **Tải tài liệu**. Nếu tab cũ còn giữ bundle trước đó, tải lại trang.
2. Chọn hoặc kéo thả lần lượt WebP, BMP, TIF một trang, TIFF nhiều trang dưới 10 MB. Kiểm tra mô tả định dạng, loading state và tự chuyển tới trang chi tiết.
3. Kiểm tra tên file, preview, OCR và extraction. Với TIFF nhiều trang, bấm **Trang sau/Trang trước**, đối chiếu nội dung OCR theo thứ tự trang.
4. Sửa văn bản OCR, chờ trạng thái đã lưu; sửa dữ liệu trích xuất và lưu. Tải lại trang để kiểm tra dữ liệu.
5. Xác nhận kết quả, xuất JSON, kiểm tra `ocr_text_raw` giữ nội dung nhận dạng ban đầu và `ocr_text` chứa bản hiệu chỉnh. Mở lại rà soát, sửa tiếp rồi xóa tài liệu.
6. Lặp lại PDF/PNG/JPG/JPEG. Thử GIF/HEIC, file rỗng, file đổi đuôi giả hoặc trên 10 MB và kiểm tra thông báo từ chối.

## Giới hạn kiểm chứng

Đã kiểm chứng bằng test component/API và Tesseract thật với mẫu tổng hợp; chưa thao tác trình duyệt thủ công trên mọi trình duyệt hoặc đo chất lượng OCR trên bộ tài liệu thực tế của người dùng. Các kiểu nén TIFF hiếm và file từ thiết bị scan riêng vẫn phụ thuộc khả năng decoder Pillow/libtiff. WebP/PNG động giữ hành vi OCR trang đầu; hỗ trợ nhiều trang trong thay đổi này dành cho TIFF. Giới hạn pixel/trang và đọc tuần tự giúp chặn tải quá lớn, nhưng chưa benchmark tải đồng thời ở sát các giới hạn trên.
