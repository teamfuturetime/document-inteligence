# Tiền xử lý tài liệu — P3-01

Module `document_pipeline.preprocessing` chạy thật, độc lập FastAPI. Nó chuẩn
hóa một trang để chuẩn bị cho OCR; không đọc chữ hoặc trích xuất hóa đơn.
API `/api/v1/extract` vẫn trả fixed mock như [mock demo](mock-demo.md).

## Chạy thử

Từ repository root, trên [nhánh tích hợp cá nhân](personal-integration.md):

```bash
uv sync --locked
.venv/bin/python -m document_pipeline.preprocessing data/samples/synthetic-001.png --output /tmp/ai02-prepared/image.png
.venv/bin/python -m document_pipeline.preprocessing data/samples/synthetic-001.pdf --output /tmp/ai02-prepared/pdf.png --dpi 150
```

Mỗi lần tạo PNG grayscale và file cùng tên có đuôi `.metadata.json` bên cạnh.
Output chỉ nằm ở đường dẫn bạn chọn; dùng thư mục tạm hoặc `data/generated/`
đã ignore. Không dùng dữ liệu cá nhân thật. CLI trả exit code 1 với mã lỗi khi
input không hợp lệ. Đường dẫn output đã tồn tại sẽ được ghi đè.

Python callers dùng `prepare_document(data, PreprocessingConfig(...))`, nhận
`PreparedPage.image` là Pillow image độc lập file/worker và `.metadata` là dict.
Lỗi dự kiến dùng `PreprocessingError.code`.

## Chuẩn hóa và giới hạn

- PNG/JPEG: xác minh cấu trúc, áp dụng cả tám hướng EXIF, ghép alpha lên nền
  trắng, chuyển grayscale `L`. Giữ nguyên kích thước sau sửa hướng.
- PDF: PyMuPDF render đúng một trang, mặc định 150 DPI; có thể chọn 72–300 DPI.
  Không chấp nhận PDF có mật khẩu, cần sửa cấu trúc hoặc nhiều trang.
- Tối đa 10 MiB input và 25 triệu pixel output; kiểm tra ngân sách pixel trước
  khi decode/render. Ảnh động nhiều frame cũng bị từ chối.
- Mỗi tài liệu xử lý trong subprocess riêng. Timeout mặc định 30 giây;
  parent dừng và thu hồi worker khi quá hạn, kể cả native PDF render. PyMuPDF
  không được chạy trong thread của backend. Dữ liệu truyền qua stdin/stdout,
  worker không tạo file tạm. Đây không phải sandbox bảo mật hoặc giới hạn RSS.
- Chưa deskew, threshold, denoise hoặc phóng to ảnh. Các bước đó cần evidence
  chất lượng OCR trước khi bổ sung.

Các mã lỗi: `invalid_document`, `unsupported_media_type`, `multiple_pages`,
`file_too_large`, `image_too_large`, `processing_timeout`, `internal_error`.
Đây là lỗi của module Python, chưa bổ sung mapping HTTP mới.

## Metadata và tọa độ

Metadata ghi `preprocessing_version`, config, SHA-256 của config/input,
media type, kích thước output/source, page 1 và `color_mode=L`.
Dependency versions được pin trong `uv.lock`.

`to_original` là ma trận 3×3 row-major, ánh xạ tọa độ output sang source.
Tọa độ là cạnh pixel liên tục, gốc trên trái; bounding box dùng cạnh phải/dưới
exclusive theo contract. Khi ánh xạ box qua xoay/lật, biến đổi cả bốn góc rồi
lấy min/max.

- Ảnh: `source_coordinate_space=raw_image_pixels`, kích thước source trước
  xoay EXIF. Browser có thể tự xoay preview, nên phải thống nhất hệ tọa độ
  khi tích hợp overlay; không áp dụng EXIF hai lần.
- PDF: `source_coordinate_space=pdf_raster_pixels`, source chính là raster
  ở DPI đã chọn nên ma trận identity. Không phải tọa độ PDF points.
  Metadata ghi thêm DPI và kích thước trang points. Chưa crop/deskew/scale
  riêng sau rasterization.

## Verification local

Ngày 2026-10-15, macOS ARM64/Python 3.13.14:

- 32 pipeline tests: PNG/JPEG/PDF thật, tám hướng EXIF và ánh xạ pixel,
  alpha, ảnh động, PDF lỗi/mật khẩu/đa trang, giới hạn, timeout worker thật,
  config và tính lặp lại.
- Bộ Python workspace: 117 tests pass; export 9 schema không drift.
- CLI chạy thành công trên sample PNG và PDF, tạo PNG grayscale 1200×1600
  và metadata bên ngoài repository.

Đây là evidence local; thay đổi P3-01 chưa chạy GitHub CI. Workflow pytest
hiện có tự thu thập `pipeline/tests` nhờ cấu hình root.

Task kế tiếp là P3-02: adapter Tesseract tiếng Việt. Máy đã có Tesseract nhưng
chưa có language model `vie`; chưa tuyên bố OCR sẵn sàng.

Tham khảo [Pillow EXIF transpose](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose),
[PyMuPDF rasterization](https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_pixmap)
và [giới hạn threading](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html).
