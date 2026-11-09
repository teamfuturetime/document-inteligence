# Sửa Hủy OCR: khôi phục ngay bản đã lưu

## Nguyên nhân thực tế

Đã kiểm tra `OCRTextCard`, `DocumentDetailPage` và tiện ích theo dõi draft:

- Gõ chỉ cập nhật `draftOcrText` và `draftRef`; không cập nhật `savedOcrText` hay gọi callback lưu của component cha.
- Textarea đã được controlled bằng `value={draftOcrText}`.
- `savedOcrText` chỉ nhận dữ liệu backend và acknowledgement của lần lưu thành công. Khi đang sửa, effect không tự đồng bộ props đè lên bản nháp.
- Callback `cancel()` cũ chờ `window.confirm()`. Nếu không xác nhận, hàm thoát trước khi reset nên textarea giữ bản nháp. Nếu xác nhận, callback reset rồi đặt `editing=false` và tháo textarea khỏi DOM. Cả hai nhánh không đáp ứng yêu cầu “bấm Hủy thì textarea lập tức hiển thị lại bản đã lưu”.

Sửa trực tiếp callback: bỏ điều kiện xác nhận, reset draft và ref về `savedOcrText`, giữ editor mở. Không reload hay đọc lại OCR gốc để khôi phục. Cách này cũng tránh kích hoạt effect dành cho lúc thoát editor sau khi Hủy.

## Hành vi sau sửa

- Hủy lập tức hiển thị lại bản được backend xác nhận gần nhất trong cùng textarea.
- Xóa trạng thái chưa lưu, lỗi, thông báo thành công và trạng thái copy; nút Lưu OCR bị khóa cho tới khi có thay đổi mới.
- Nếu vừa lưu thành công rồi sửa tiếp, Hủy dùng bản vừa được xác nhận, kể cả khi props cha chưa kịp cập nhật; không quay về raw OCR hay revision cũ.
- Khi lưu thất bại, draft được giữ. Hủy khôi phục bản đã lưu trước lần thất bại và không retry.
- Khi đang lưu, nút Hủy bị disabled và callback còn kiểm tra `inFlight`. Sau khi phản hồi đến, người dùng mới có thể Hủy phần nhập tiếp về bản vừa được backend xác nhận. Không cố hủy request đã gửi hoặc giả định có thể hoàn tác database bằng thao tác local.
- Nhãn “Đã được người dùng chỉnh sửa” vẫn dựa trên prop `corrected` từ backend. Gõ và Hủy không đổi nhãn đó.
- Manual save giữ nguyên; không có API lưu khi Hủy, không autosave, không sửa backend/pipeline/schema/upload ảnh.

## File của lần sửa này

1. `frontend/src/components/OCRTextCard.tsx`: sửa callback Hủy.
2. `frontend/src/components/OCRTextCard.cancel.test.tsx`: thêm regression TC01–TC09 cho saved/draft, tab, lỗi và phản hồi muộn.
3. `frontend/src/components/OCRTextCard.test.tsx`: cập nhật kỳ vọng textarea vẫn mở và không gọi confirm khi Hủy.
4. `frontend/src/components/OCRTextCard.autosave.test.tsx`: cập nhật test khôi phục bản lưu mới nhất ngay trong editor.
5. `frontend/src/components/OCRTextCard.network.test.tsx`: kiểm tra Hủy không gọi bất kỳ HTTP request nào.
6. `frontend/src/contexts/AuthContext.test.tsx`: cập nhật test Hủy xóa dirty để đăng xuất không hỏi lại.
7. `docs/ocr-explicit-save.md`: cập nhật mô tả Hủy hiện tại.
8. `docs/ocr-cancel-fix.md`: báo cáo này.

Các file hỗ trợ upload và manual save khác đã có trong workspace được giữ nguyên trong lần sửa này. Không thêm dependency, commit hoặc push.

## Kiểm thử

| Kiểm tra | Kết quả |
| --- | --- |
| `npm.cmd test` | 91 PASS, 11 file; không FAIL |
| `npm.cmd run build` | PASS |
| `npm.cmd run typecheck` | PASS |
| `npm.cmd run lint` | PASS |
| `.venv/Scripts/python.exe -m pytest -q -rs` | 243 PASS, 1 SKIP; không FAIL |
| Edge headless trên `http://localhost:3000` | TC01–TC09 PASS |

SKIP có sẵn: test storage không tạo được symlink trên Windows. Warning deprecation của dependency và cảnh báo fixture TIFF hỏng vẫn như trước.

Regression đã chạy gồm raw OCR, revision/concurrency, manual save, review, confirm, reopen, export JSON, authentication/CSRF/ownership và upload/preview PDF/PNG/JPEG/WebP/BMP/TIFF.

## Browser và Network

Edge tải bản frontend Docker đã cập nhật tại **localhost:3000**. Chỉ trong tab kiểm thử, CDP chuyển tiếp API tới FastAPI thật với SQLite và thư mục tạm riêng tại cổng 8012; không ghi vào PostgreSQL đang sử dụng. Một response 500 được giả lập và một request được giữ chậm có chủ đích để kiểm tra lỗi và async.

- TC01/05/06: sửa rồi Hủy → textarea về “HÓA ĐƠN THANH TOÁN”, dirty bị xóa, Lưu OCR disabled, không có hộp thoại hoặc request ghi; revision database vẫn 3.
- TC02: reload sau Hủy → dữ liệu backend giữ nguyên, không có cảnh báo chưa lưu.
- TC03: lưu thành công tăng revision lên 4, sửa tiếp rồi Hủy → khôi phục bản mới nhất, không tăng revision.
- TC04: đổi qua raw/structure/readable rồi Hủy → khôi phục đúng bản đã lưu.
- TC07: lưu lỗi giữ draft; Hủy xóa lỗi và khôi phục bản đã lưu, không tự retry.
- TC08: giữ request đang chờ → Hủy disabled. Gõ tiếp rồi nhận acknowledgement revision 5 → Hủy khôi phục bản revision 5; phản hồi không áp lại draft đã bỏ.
- TC09: raw OCR không đổi; nhãn đã chỉnh sửa chỉ có cho tài liệu thực sự có correction đã lưu; review, confirm, reopen và export JSON hoạt động.

**Tổng request lưu do Hủy tạo ra: 0.** Ba PATCH trong log đều bắt đầu bằng nút Lưu OCR: lần thành công, lần giả lập lỗi và lần giữ phản hồi chậm.

Log: `storage/ocr-cancel-verification/browser-network.json` (thư mục storage không đưa vào Git). Frontend đã được dựng lại và chạy tại localhost:3000. Chưa kiểm chứng mọi trình duyệt; lần này đã kiểm chứng bằng Edge thật ở chế độ headless.
