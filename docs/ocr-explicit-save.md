# Chỉ lưu OCR khi nhấn “Lưu OCR”

## Nguyên nhân và phạm vi

`OCRTextCard.tsx` có effect debounce 800 ms tự gọi `save()` khi bản nháp thay đổi. Cơ chế khôi phục bản nháp từ sessionStorage cũng có thể kích hoạt effect đó. Backend không có autosave: correction chỉ được ghi qua PATCH `/api/v1/documents/{id}/ocr-correction` sau khi xác thực session, CSRF, ownership, trạng thái và revision.

Thay đổi này chỉ sửa mã frontend và bổ sung kiểm thử. Không sửa mã backend, schema, pipeline OCR hoặc phần hỗ trợ upload/preview WebP/BMP/TIFF đã triển khai trước đó.

## Cơ chế mới

- `savedOcrText`: bản đã nhận từ backend hoặc được backend xác nhận sau lần lưu thành công.
- `draftOcrText`: bản đang nhập trong React state, không ghi nội dung OCR vào sessionStorage.
- Gõ, xóa, blur, chờ, chuyển tab, chuyển trang và unmount không gọi API lưu. Không còn effect/timer autosave; timer còn lại trong component chỉ xóa trạng thái “Đã sao chép”.
- Nút “Lưu OCR” là nơi duy nhất gọi hàm lưu. Nút chỉ bật khi có thay đổi chưa lưu, tài liệu cho phép sửa và không có request đang thực hiện. Ref chặn cả các lần nhấn liên tiếp trước khi React cập nhật trạng thái disabled.
- Sau khi backend xác nhận đúng nội dung và revision mới, cập nhật `savedOcrText` từ response và hiện thành công. Nếu người dùng tiếp tục gõ trong lúc request đang chạy, bản mới vẫn chưa lưu và cần bấm nút lần nữa.
- Lỗi mạng, lỗi máy chủ, conflict hoặc response không xác nhận đúng nội dung: giữ bản nháp, không cập nhật bản đã lưu, không tự retry. Người dùng có thể bấm lưu lại. Request lỗi mạng có thể có kết quả không xác định ở server; revision vẫn bảo vệ việc ghi đè khi retry.
- “Hủy” khôi phục ngay bản đã lưu gần nhất trong textarea và giữ editor mở, không chờ hộp thoại xác nhận, không gửi request ghi. Xóa dirty, lỗi và thông báo lưu thành công. Nút Hủy bị khóa khi request lưu đang chờ phản hồi. Request do người dùng đã bấm lưu vẫn có thể hoàn tất nếu họ xác nhận rời trang sau đó; không có request mới do unmount.
- Chuyển giữa ba tab OCR giữ bản nháp nên không cần cảnh báo bỏ bản nháp. Điều hướng sang tài liệu/trang khác, kể cả Back, được chặn bằng `useBlocker`; tải lại/đóng tab dùng `beforeunload`. Đăng xuất tiếp tục dùng cảnh báo có sẵn, với metadata dirty trong bộ nhớ, không lưu nội dung bản nháp.

Entry point chuyển từ `BrowserRouter` sang `createBrowserRouter`/`RouterProvider` để dùng cơ chế chặn điều hướng chính thức; giữ nguyên route tree và đường dẫn của `App`. [React Router mô tả `useBlocker`](https://reactrouter.com/api/hooks/useBlocker) dành cho điều hướng SPA; hard reload cần `beforeunload` riêng.

## File của thay đổi này

| File | Nội dung |
| --- | --- |
| `frontend/src/components/OCRTextCard.tsx` | Bỏ debounce và lưu/khôi phục nội dung qua sessionStorage; tách saved/draft và lưu qua nút |
| `frontend/src/utils/ocrDrafts.ts` | Metadata dirty trong bộ nhớ để cảnh báo đăng xuất; giữ xử lý riêng tư cho draft cũ |
| `frontend/src/main.tsx` | Router hỗ trợ chặn điều hướng |
| `frontend/src/pages/DocumentDetailPage.tsx` | Cảnh báo rời trang/đổi tài liệu bằng blocker; không đổi logic review |
| `frontend/src/components/OCRTextCard.autosave.test.tsx` | Cập nhật bộ test autosave cũ thành regression bảo đảm chỉ lưu thủ công |
| `frontend/src/components/OCRTextCard.network.test.tsx` | Kiểm tra HTTP thật qua `api.saveOcr`: không request khi nhập, một PATCH khi nhấn nút |
| `frontend/src/pages/DocumentDetailPage.test.tsx` | Test routing, Back, reload, confirm/reopen/export và revision với lưu thủ công |
| `frontend/src/contexts/AuthContext.test.tsx` | Kiểm tra đăng xuất với draft chỉ tồn tại trong React state |
| `tests/integration/test_document_review.py` | Bổ sung test GET không sửa dữ liệu và PATCH hợp lệ mới cập nhật correction |
| `docs/ocr-explicit-save.md` | Báo cáo và hướng dẫn kiểm tra |

Các thay đổi hỗ trợ định dạng ảnh có sẵn trong workspace được giữ nguyên. Không thêm dependency, commit, push hoặc merge.

## Kết quả kiểm thử triển khai manual save ban đầu

Kết quả mới nhất sau khi sửa nút Hủy: xem [báo cáo sửa Hủy](ocr-cancel-fix.md).

| Kiểm tra | Kết quả |
| --- | --- |
| `npm.cmd test` trong frontend | 82 PASS, 10 file |
| `npm.cmd run build` | PASS |
| `npm.cmd run typecheck` | PASS |
| `npm.cmd run lint` | PASS |
| `.venv/Scripts/python.exe -m pytest -q -rs` | 243 PASS, 1 SKIP, không FAIL |
| Edge headless + production frontend build + FastAPI thật với SQLite riêng | PASS |

SKIP có sẵn: `tests/unit/test_storage.py` không tạo được symlink trên môi trường Windows. Các warning deprecation của dependency và warning fixture TIFF hỏng không làm test thất bại.

TC01–TC10 được bao phủ bởi test component, HTTP, routing và database. Đã kiểm tra raw OCR, revision/conflict, review, confirm, reopen, export JSON, authentication/CSRF/ownership, cùng regression upload/preview các định dạng ảnh.

Kiểm chứng Edge dùng tài khoản/tài liệu tổng hợp, database và thư mục tạm riêng; không ghi vào PostgreSQL đang chạy. Theo dõi qua Chrome DevTools Protocol (cùng nguồn sự kiện Network của DevTools):

- Gõ, chờ 5 giây, blur và đổi cả ba tab: **0 request lưu**, revision database giữ **0**.
- Tải lại khi chưa lưu: có `beforeunload`, backend vẫn là nội dung ban đầu, **0 request lưu**.
- Nhấn “Lưu OCR”: **1 PATCH**, backend đổi sang nội dung đã gửi và revision **1**; raw OCR giữ nguyên.
- Nhấn Hủy sau lần lưu đầu: giữ nội dung đã lưu, không thêm PATCH.
- Giả lập một response 500: giữ bản nháp, backend revision vẫn **1**, không tự retry; nhấn lưu lại mới gửi PATCH tiếp và tăng revision **2**.
- Điều hướng bằng link khi dirty: hộp thoại xác nhận xuất hiện, chọn ở lại giữ bản nháp; confirm, reopen và export JSON hoạt động.

Log chi tiết ở `storage/ocr-manual-verification/browser-network.json` trong workspace (thư mục storage không đưa vào Git). Tổng ba PATCH trong log tương ứng ba lần bấm nút: lần lưu đầu, lần giả lập lỗi và lần retry thủ công. Không có PATCH phát sinh từ nhập liệu.

## Kiểm tra thủ công

1. Tải lại `http://localhost:3000`, mở một tài liệu đã xử lý, bật DevTools → Network và lọc `ocr-correction`.
2. Bấm “Chỉnh sửa văn bản OCR”, nhập/xóa nội dung, chờ, click ra ngoài và đổi qua lại ba tab: không có PATCH/PUT/POST lưu OCR.
3. Bấm “Lưu OCR”: có đúng một PATCH; chỉ hiện thành công khi backend trả về. Nút lưu bị khóa trong lúc gửi và khi không còn thay đổi.
4. Sửa tiếp rồi bấm “Hủy”: quay về nội dung đã lưu, Network không thêm request ghi. Tải lại để kiểm tra dữ liệu.
5. Tạo bản nháp rồi thử Back, link điều hướng, tải lại hoặc đăng xuất: kiểm tra cảnh báo. Xác nhận rời trang sẽ bỏ bản nháp local.
6. Thử lưu khi offline: giữ bản nháp và hiện lỗi, không tự gửi lại khi online. Bấm nút để retry.
7. Kiểm tra tab OCR gốc, sửa dữ liệu trích xuất, xác nhận, xuất JSON và mở lại rà soát như trước.

Đã kiểm chứng tự động trên Edge headless; chưa kiểm tra trên mọi trình duyệt. Nội dung/cách hiển thị hộp thoại `beforeunload` do trình duyệt quyết định. Draft chỉ trong React state sẽ mất nếu người dùng xác nhận bỏ trang hoặc trình duyệt đóng cưỡng bức.
