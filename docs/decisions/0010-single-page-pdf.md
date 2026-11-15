# ADR-0010 — PDF một trang trong pipeline local

Đề xuất review trong [#24](https://github.com/teamfuturetime/document-inteligence/issues/24), thuộc [#6](https://github.com/teamfuturetime/document-inteligence/issues/6). Nền khảo sát `main@921541d`. Liên quan MVP-01, MVP-02, MVP-04, ENG-03 và ENG-04 theo [scope](../requirements/scope.md).

| Phần | Đặc tả |
| --- | --- |
| Đầu vào | Body nhị phân có header file `%PDF-`, marker `%%EOF` cuối file (cho phép whitespace cuối), parser mở được và đúng một trang. Nhận diện theo nội dung, độc lập tên file và MIME của client. |
| Admission | Dùng chung cap mặc định 5 MiB, deadline nhận body 30 giây, hai upload đang xử lý. Từ chối trước khi tạo document/run/event/source/preview. |
| Raster | PDFium render local 200 DPI, nền trắng, áp orientation/crop của PDF. Trước cấp bitmap tính ceiling kích thước render từ kích thước trang hữu hạn và dương. Tối đa 8192 pixel mỗi chiều và `max_image_pixels` (mặc định 16 triệu); kiểm lại bitmap thực và ảnh sau scale. |
| Deadline | Subprocess preview tối đa min(5 giây, timeout pipeline). OCR dùng cùng renderer và raster trong deadline pipeline 30 giây mặc định. Nhận body có budget riêng. |
| Preview/evidence | Giữ raw PDF và hash trong storage nội bộ. /image trả PNG. Gốc frame trên trái của trang đã raster. Nếu OCR scale/rotate thêm, chiếu ngược về frame preview bằng transform hiện có. |
| Phạm vi | Cả hai schema giữ cùng pipeline, hóa đơn là luồng nghiệm thu PDF. Hỗ trợ PDF scan và PDF có chữ qua raster OCR. Không bật JavaScript, không mở file đính kèm hay dùng fallback fixture. |

| HTTP | Mã lỗi |
| --- | --- |
| 415 | `UNSUPPORTED_CONTENT_ENCODING` cho HTTP content encoding khác identity; base64 không được tự giải mã. |
| 415 | `INVALID_PDF` khi cấu trúc bị từ chối, `PDF_ENCRYPTED` khi có mã hóa kể cả empty password, `PDF_PAGE_COUNT` khi khác một trang. |
| 413 | `FILE_TOO_LARGE` (byte cap), `IMAGE_TOO_LARGE` (raster cap). |
| 408 | `PROCESSING_TIMEOUT` cho preview PDF hết hạn. Timeout OCR sau admission ghi vào run lỗi. |

Giữ khóa retry, review CAS, prediction bất biến, database và nghĩa JSON export 1.0.0. Thêm MIME types trong capabilities và sinh lại OpenAPI/types theo app version mới. Subprocess, cap và deadline giảm rủi ro, với phạm vi local/synthetic hiện tại. Chúng không đặt trần RSS cứng.

## Lựa chọn renderer và thử nghiệm

Kế thừa cách cô lập parser và kiểm trước raster từ nhánh Tùng `personal/canhtung-main@61a31ab`, tham khảo kiểm nội dung file ở `congtri@66074f4`. Chọn [pypdfium2](https://pypdfium2-team.github.io/pypdfium2/readme.html) 5.15.2 với PDFium local, ghi version thực trong run và giữ license notices của wheel khi phân phối.

Thử trên Windows/Python 3.14.5 ngày 15/11/2026 với PDFium 159.0.8149.0. Đóng gói ảnh synthetic `hoa_don_007.png` bằng Pillow ở 200 DPI thành PDF 58.935 bytes. PDFium đọc một trang 432 × 558 pt và render 1200 × 1550 px trong 16,0 ms cho một lượt sau khi import. Số đo chỉ gồm mở/render, chưa gồm subprocess, OCR hoặc mạng.

## Nghiệm thu

- Pipeline kiểm PNG/JPEG, PDF lỗi, mã hóa, nhiều trang, kích thước quá lớn, timeout và PDF có rotation.
- API kiểm mã lỗi, không phát sinh dữ liệu khi reject, retry giữ document/run, kích thước preview khớp frame inference.
- Browser với OCR thật kiểm PDF → chọn vùng OCR → sửa/lưu/reload → xác nhận → tải JSON. Chạy lại flow PNG/JPEG, đơn đề nghị, explicit-null, CAS và lịch sử.
