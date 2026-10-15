# P2-03 — Upload và mock extraction

Đây là snapshot demo mock P2-03. Hiện backend mặc định real; muốn chạy hướng
dẫn mock dưới đây cần đặt `VDI_MODE=mock` trước khi khởi động backend.
Luồng hiện tại xem [final-demo.md](final-demo.md).

Đây là luồng kiểm thử tích hợp, chưa chạy OCR hoặc rules extraction thật.
Mọi tài liệu hợp lệ nhận cùng năm giá trị từ hóa đơn synthetic SYN-0001,
không phải dữ liệu suy ra từ file. Mỗi request có document_id mới, `mode=mock`,
`ocr_version=mock-not-run`, confidence null/evidence rỗng và warnings
`mock_data`, `not_derived_from_upload`.

## Kiểm tra backend

Từ root chạy `uv sync --locked`, rồi mở server:

```bash
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000
```

Ở terminal khác, từ root:

```bash
curl --fail --form 'file=@data/samples/synthetic-001.png' http://127.0.0.1:8000/api/v1/extract
```

Thay PNG bằng JPG/PDF tương ứng để thử ba định dạng. Schema response vẫn
v1.0.0. `GET /health` vẫn báo OCR chưa sẵn sàng, không coi upload mock là OCR.

## Thử luồng frontend

Trong terminal khác: `cd frontend`, `npm ci`, `npm run dev`. Mở
`http://127.0.0.1:5173/`, chọn mẫu ở `data/samples/` rồi bấm **Gửi và xem mock**.
UI hiển thị trạng thái gửi, lỗi có thể retry và năm giá trị được gắn nhãn mock.
Chọn file khác hoặc bỏ chọn hủy request và xóa kết quả cũ. Không tự động upload
ngay khi chọn file. Chưa có preview/review/edit/JSON export.

API client kiểm tra JSON Schema lúc runtime và date format; proxy `/api` đi đến
backend 8000. Timeout client upload là 30 giây, health là 5 giây. Timeout client
không chứng minh server đã dừng tác vụ; backend vẫn cần hard deadline pipeline
khi tích hợp OCR thật.

## Giới hạn và xử lý tài liệu

- File tối đa 10 MiB; request tối đa 10 MiB + 64 KiB overhead multipart.
  Byte được đếm khi đọc stream, không phụ thuộc Content-Length. Overhead lớn
  bất thường cũng bị 413. Không nhận thêm field hoặc nhiều file.
- Deadline 30 giây cho nhận request body. Chưa có hard deadline CPU/OCR;
  giới hạn thực thi OCR phải bổ sung khi tích hợp pipeline thật.
- Kiểm tra nội dung bằng decoder, không tin filename/declared MIME. Backend
  không dùng filename làm path và không lưu lịch sử/file upload.
- PNG/JPEG phải decode được, ≤ 25 megapixel và một frame. Input rỗng/corrupt
  bị 422; định dạng không hỗ trợ bị 415. PDF phải mở được, một trang, không
  có mật khẩu. Hiện kiểm tra cấu trúc PDF, chưa render/preprocess trang PDF;
  budget raster PDF thuộc Phase 3.
- Parse multipart sau khi giới hạn body. Context manager đóng UploadFile trên
  success và validation error; parser đóng handles khi parse lỗi. Decode chạy
  threadpool để không chặn event loop. Raw body/file bytes vẫn giữ có giới hạn
  trong memory; MVP chưa có queue hoặc quản lý concurrency riêng.
- Lỗi trả envelope contract; không echo file contents, tên file hay traceback.

## Kiểm thử

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m backend.export_schemas --check
```

Backend/data: 85 tests pass, không warning; 9 schema không drift. PDF metadata
validation dùng pypdf trong threadpool; không dùng PyMuPDF trong server đa
luồng. Samples render tooling vẫn ở môi trường riêng.
Các case upload gồm ba định dạng, corrupt/empty, PDF đa trang/password,
over-limit, MIME/filename giả, multipart sai/duplicate, stream không có length,
đóng file trên success/error và phân biệt fixed mock với kết quả thật.

Các fixture synthetic trong Phase 1 không được sửa hoặc gọi là kết quả AI.
Không dùng demo mock để tính evaluation. Review/edit/validation/export chưa
triển khai; các task đó vẫn dùng contract baseline đã định nghĩa.

Frontend: 30 Vitest tests pass; build/typecheck/9 generated contract check pass.
HTTP smoke test qua Vite proxy nhận 200 đúng contract cho PNG/JPG/PDF và 415
đúng error envelope cho file giả. Server tạm đã dừng sau verification. Chưa
visual QA bằng browser, chưa GitHub CI/deploy.
