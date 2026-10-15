# Frontend

React + TypeScript + Vite. Upload/preview PNG/JPG/PDF, kết quả OCR, chỉnh sửa
năm field, validation lỗi từng field và tải ReviewedExport JSON giữ provenance.
Không chứa engine OCR hoặc logic field extraction.

Node theo engines package.json, đã kiểm tra 26.5.0/npm 11.17.0.
Chạy backend real/model trước theo [development](../docs/development.md), rồi:

```bash
npm ci
npm run dev
```

Mở http://127.0.0.1:5173/. Vite proxy /health,/api tới 8000, có thể override bằng
VDI_BACKEND_URL. Nếu server mock thì UI gắn nhãn rõ và giữ mode trong export.

```bash
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Build kiểm tra 9 generated TS contracts, typecheck và static bundle. Runtime
JSON được kiểm tra bằng AJV; validation còn kiểm tra consistency null/errors.
E2E dùng backend thật/native OCR, download JSON và kiểm tra Pydantic contract.
Server tests riêng 18000/15173; model ở ../data/models/tessdata. Playwright
traces/screenshots nằm ở test-results đã ignore. Xem [review/export](../docs/review-export.md)
và [completion evidence](../docs/completion.md).

File picker là kiểm tra sơ bộ; backend kiểm tra nội dung/limits thật. Đổi file
hủy request cũ và xóa kết quả; mỗi edit/reset vô hiệu validation, response muộn
không bật export. Object URLs được cleanup. PDF native viewer có link tải dự phòng.
Không highlight box lên preview vì tọa độ processed khác raw/EXIF/PDF preview.

Chưa deploy: production cần same-origin reverse proxy cho API, không dùng dev
proxy như cấu hình hosting. Không đưa secrets vào frontend hoặc localStorage.
