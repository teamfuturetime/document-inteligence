# Review và xuất JSON — Phase 5

Chọn tài liệu để xem preview ảnh hoặc PDF native của trình duyệt; nếu PDF
không được hỗ trợ, tải bản gốc để đối chiếu. Object URL được thu hồi khi đổi
file/unmount. UI không ghi upload vào localStorage hoặc lưu ở server.

Bấm **Trích xuất hóa đơn**, đối chiếu năm field với tài liệu, xem confidence,
warnings và evidence token/box processed trong phần mở rộng. Chưa highlight
box lên preview; tránh nhầm hệ tọa độ EXIF/raster PDF.

Sửa giá trị → **Kiểm tra dữ liệu** → **Xuất JSON đã xác nhận**. Mỗi edit/reset/
đổi tài liệu hủy request cũ và vô hiệu validation; response đến muộn không
thể bật export. Field errors hiển thị cạnh input, có nhãn/aria-invalid.

JSON tải về đúng ReviewedExport v1, gồm `original_extraction`, giá trị cuối đã
normalize và `edited_fields` theo giá trị normalized khác AI. Không gán thêm
confidence cho dữ liệu người dùng sửa. Mode mock vẫn giữ nguyên và được gắn
nhãn rõ; real backend mặc định chạy pipeline thật.

Vitest kiểm tra edit/reset/stale response/invalid fields/export provenance/
cleanup preview. Phase 7 có Playwright E2E xuyên backend thật, download JSON
và kiểm tra contract; xem [completion.md](completion.md) cho evidence cuối.
