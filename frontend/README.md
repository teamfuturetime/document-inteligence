# Frontend

Owner: thành viên 2 — Frontend/Review UI.

P2-02 có React + TypeScript + Vite và health client. P2-03 thêm upload client
`POST /api/v1/extract`, kết quả mock và trạng thái loading/error/retry. Không
chứa logic OCR/extraction. Preview, review/edit và export chưa triển khai.

## Chạy local

Yêu cầu Node.js 22.22.2+ trong nhánh 22, 24.15.0+ trong nhánh 24 hoặc 26+ và npm
(theo engines của jsdom). Thực tế kiểm tra Node 26.5.0/npm 11.17.0.
Chạy backend ở terminal riêng theo [development.md](../docs/development.md),
sau đó từ thư mục `frontend/`:

```bash
npm ci
npm run dev
```

Mở `http://127.0.0.1:5173/`; bấm **Kiểm tra kết nối**. Vite proxy `/health` và `/api` đến
`http://127.0.0.1:8000`, vì vậy dev không cần thêm CORS vào backend.
Backend báo Mock/OCR chưa sẵn sàng. Chọn sample synthetic rồi bấm **Gửi và xem
mock**. Kết quả cố định, không dựa vào file; xem [mock demo](../docs/mock-demo.md).

## Kiểm tra và contract

```bash
npm test
npm run build
```

Build bao gồm contract drift check và typecheck. Types trong `src/api/generated/`
được sinh từ 9 schema tại `../schemas/v1/`; không sửa bằng tay. Khi schema thay
đổi: chạy `npm run contracts:generate`, review schema/types cùng nhau và chạy
tests/build. API client dùng schema chung kiểm tra payload lúc runtime bằng AJV;
type TypeScript không bảo đảm JSON từ network đúng cấu trúc. `ajv-formats`
kiểm tra date format/calendar của extraction response. Upload dùng FormData,
browser đặt multipart boundary; đổi/bỏ file hủy request và xóa kết quả cũ.

`package-lock.json` khóa dependencies, dùng `npm ci` trên checkout mới.
Generated `.d.ts` được track vì là interface; `node_modules/` và `dist/` bị ignore.

File picker chỉ kiểm tra extension/MIME/size client: PNG/JPG/PDF, 10 MiB,
non-empty. Không kiểm tra nội dung decode/số trang; backend phải kiểm tra thật
khi triển khai upload. Chỉ dùng dữ liệu synthetic trong `../data/samples/`.

## Deployment status

`npm run build` tạo static assets, chưa deploy. Proxy của Vite phục vụ chạy
local, không cấu hình API trên hosting production. Production hosting sau này
cần reverse proxy cùng origin đến backend `/health` và API tương ứng.
Không đưa secret vào frontend env vì nó được gửi tới trình duyệt.

Đã chạy 30 Vitest tests, typecheck, contract check và build. HTTP smoke check
qua Vite proxy upload PNG/JPG/PDF trả mock đúng contract và file giả nhận 415.
Không có browser connector
trong phiên làm việc để thực hiện visual QA trên trình duyệt; các tương tác UI
được kiểm tra bằng React Testing Library/jsdom. CI GitHub chưa thiết lập.
