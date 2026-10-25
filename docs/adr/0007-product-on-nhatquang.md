# ADR-0007 — Triển khai sản phẩm local trên nhatquang

**Status:** Applied on nhatquang 24/10/2026 theo yêu cầu trực tiếp của người dùng; chưa là quyết định nền chung của nhóm. **Requirements:** MVP-01..06, DATA-01, EVD-01..04, ENG-01..04.

**Context:** main remote vẫn chỉ có README; nhatquang có foundation, các nhánh khác phát triển khác kiến trúc. Người dùng đã chọn tiếp tục cả sản phẩm trên nhatquang. Việc này thay giới hạn foundation-only của lượt khởi tạo, không thay yêu cầu gốc hoặc tự cấu hình GitHub.

**Options:** chờ nền nhóm; merge nguyên các ứng dụng cạnh tranh; hoặc mở rộng monorepo hiện có bằng pipeline package và lớp backend rõ ràng. **Decision:** phương án cuối; giữ React/FastAPI/Pydantic/uv/npm, thêm package pipeline độc lập, native Tesseract CPU, SQLite transactions và local persisted worker. OCR models dùng pin đã đối chiếu từ nhánh Tùng; source lineage ghi rõ.

**Contracts:** giữ foundation schema/examples; thêm product contracts 1.0.0 hỗ trợ hóa đơn header/totals và đơn đề nghị. Public domain backend là nguồn chuẩn, generators cập nhật JSON Schemas/OpenAPI/TS types. Pipeline DTO là implementation seam, không định nghĩa HTTP contract thứ hai.

**Correctness:** prediction bất biến theo run; review revision riêng; xóa-null explicit; check-and-write trong một SQLite transaction; confirm/export chỉ từ snapshot mới nhất persisted; reprocess không sửa review cũ. Fixture vẫn explicit và không fallback.

**Consequences:** chạy hoàn chỉnh local, có native và browser checks; cần Tesseract/model đã pin. Một worker process, không auth/multi-tenant, không cloud. Docker/remote Actions phải được xác minh riêng. Không coi metrics synthetic là đại diện tài liệu thật hoặc calibrated confidence.

**Revisit:** nhóm chọn nền chung khác, cần đa người dùng/worker, hỗ trợ PDF/multi-page/line items, thay engine hoặc schema. Khi đó port có source lineage, migrate/version và kiểm lại producer-consumer; không đè/reset nhánh ai.
