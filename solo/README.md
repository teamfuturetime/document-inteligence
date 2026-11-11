# AI-02 Solo — bản triển khai cá nhân

Ứng dụng độc lập do chủ dự án quản lý, phát triển với trợ giúp AI. Nhánh
`personal/canhtung-solo` giữ lịch sử repository; mã mới nằm hoàn toàn trong
`solo/`, không import backend, pipeline hoặc giao diện của bản tích hợp cũ.
Đây là phiên bản ứng dụng cá nhân, không phải mô hình nền tự huấn luyện.

Phạm vi: hóa đơn bán hàng và đơn đề nghị sinh viên **synthetic** một trang,
PNG/JPEG/PDF; OCR → extraction theo schema → rà soát/sửa → validation → JSON.
So sánh OCR + luật, VLM và hybrid; báo cáo trạng thái thật của từng chế độ.

## Chạy ứng dụng mới

Đã có lựa chọn **Nguồn OCR → OCR.space (API)**. API key chỉ ở backend,
không commit vào Git. Xem [cấu hình, giới hạn và kết quả thử thật](docs/ocrspace.md).

Yêu cầu macOS/Linux, Python ≥3.11, uv, Node theo `web/package.json`; Tesseract 5
trên PATH nếu chọn OCR local. Chạy từ thư mục `solo/`:

```bash
cd solo
uv sync --locked
uv run --locked python -m ai02_solo.ocr
uv run --locked uvicorn ai02_solo.api:app --host 127.0.0.1 --port 8100
```

Terminal khác, từ repository root:

```bash
cd solo/web
npm ci
npm run dev
```

Mở **http://127.0.0.1:5174**. Chọn đúng loại tài liệu, chế độ **OCR + luật**,
upload `solo/data/golden-v1/invoice-001.png` hoặc `application-001.png`.
Đối chiếu/sửa, **Kiểm tra dữ liệu**, rồi **Xuất JSON đã xác nhận**. Mẫu `*-003`
thiếu trường cần người review bổ sung. Bản này dùng cổng riêng 8100/5174.

Giao diện có bàn làm việc gồm tài liệu gốc và các trường rà soát cạnh nhau trên
desktop, xếp dọc trên điện thoại. Có thể kéo thả một file hoặc bấm **Dùng hóa
đơn mẫu** để mở nhanh mẫu synthetic có sẵn; thao tác này chỉ tải ảnh trong ứng
dụng, chưa gửi đến OCR. Chọn nguồn rồi bấm **Trích xuất dữ liệu** để xử lý.
Ảnh có nút thu/phóng và vừa khung; PDF dùng trình xem của trình duyệt.
Đổi/xóa tài liệu hoặc đổi cấu hình sẽ hủy kết quả và validation cũ. Confidence
luôn thuộc kết quả OCR gốc, không thay đổi theo nội dung bạn sửa.

Font IBM Plex được phục vụ từ `web/public/fonts/`, kèm giấy phép OFL và nguồn
tải; giao diện không cần gọi Google Fonts khi sử dụng.

Nút mặt trời/mặt trăng ở góc trên bên phải chuyển **Sáng/Tối**, có cả trên
điện thoại. Khi chưa chọn, giao diện theo chế độ hệ thống; sau khi chọn, trình
duyệt nhớ lựa chọn cho các lần mở sau và đồng bộ giữa các tab. Nếu trình duyệt
chặn lưu trữ, nút vẫn hoạt động trong phiên hiện tại. Đổi chế độ giữ nguyên tài
liệu đang mở, các trường đã sửa và trạng thái kiểm tra dữ liệu.

Lệnh models tải đúng hai file vie/eng đã pin từ kho chính thức và kiểm tra
SHA-256 vào `.models/tessdata` (ignored). Extraction không tự tải model.

## Trạng thái và kiểm tra

Đã có cả hai schema, OCR thật, baseline luật, HTTP API, React review/validation/
JSON và bộ 36 tài liệu synthetic. Hai adapter VLM **đã có mã và kiểm thử giao
thức**, chưa cấu hình/chạy model thật theo lựa chọn của bạn. Chưa có metrics VLM.
Không phải hệ thống nhận diện mọi hóa đơn/đơn từ; baseline chỉ cho schema/layout
đã mô tả, còn sai dấu OCR và chưa được đánh giá trên dữ liệu ngoài golden.

```bash
# Từ solo/, có models và Tesseract:
SOLO_RUN_OCR=1 uv run --locked python -m pytest -q
uv run --locked python -m ai02_solo.evaluate --split test --mode rules --check
cd web
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

E2E khởi tạo backend ở 18100 và Vite ở 15174, không dùng server đang mở.
Có thể dùng Chrome đã cài thay vì tải Chromium bằng biến `SOLO_BROWSER_PATH`
trỏ tới executable. Test native được skip rõ ràng khi không đặt `SOLO_RUN_OCR=1`.
CI riêng là `.github/workflows/solo.yml`; kết quả trên GitHub phải xem theo SHA.
Code rules v2 đã pass [CI trên Linux](https://github.com/teamfuturetime/document-inteligence/actions/runs/42951239678):
43 Python tests, 4 UI tests và 7 browser E2E. Test exact match đạt 0,9111 trên
macOS/Tesseract 5.5.2 và 0,9333 trên Linux/Tesseract 5.3.4; đây là số liệu trên
dataset synthetic nhỏ, chưa có đánh giá model VLM.

Checkpoint OCR.space mới: 63 Python tests, 7 UI tests/typecheck/build, 7 browser
E2E Tesseract và một live cloud UI/export đã đạt local; thử thật trên ba định
dạng synthetic. Các baseline trên là Tesseract, không phải điểm OCR.space.

Xem [thiết kế](docs/design.md), [cấu hình VLM local/API](docs/vlm.md),
[phương pháp đánh giá](docs/evaluation.md), [bằng chứng kiểm thử và baseline](docs/verification.md),
[đọc và tự phát triển code](docs/learning.md).
