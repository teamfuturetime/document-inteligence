# Frontend

React/TypeScript/Vite. `src/app` là shell/navigation; `src/features/documents` là workflow sản phẩm; FixtureViewer giữ catalogue minh họa riêng. `src/lib/api.generated.ts` sinh từ backend OpenAPI, không sửa tay. Feature API client xử lý error codes và server export; form không tạo JSON cuối từ local state.

Cài và chạy theo [README gốc](../README.md) / scripts/dev.py; không duy trì một chuỗi setup riêng ở đây. Vite proxy `/api` về backend localhost:8000; đổi `API_PROXY_TARGET` nếu dùng cổng riêng. CORS origins backend phải khớp origin thực.

Các scripts contracts:check/typecheck/lint/format:check/test/build phải đạt. ReviewPanel tests kiểm explicit null, conflict và archived read-only; browser native workflow ở `e2e/invoice.spec.ts`, chạy bằng `python scripts/dev.py e2e`. Kết quả mới ở [consolidation verification](../docs/consolidation-verification.md); [báo cáo24/10](../docs/reports/product-verification-2026-10-24.md) là evidence lịch sử.
