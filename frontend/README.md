# Frontend

React/TypeScript/Vite. `src/app` là shell/navigation; `src/features/documents` là workflow sản phẩm; FixtureViewer giữ catalogue minh họa riêng. `src/lib/api.generated.ts` sinh từ backend OpenAPI, không sửa tay. Feature API client xử lý error codes và server export; form không tạo JSON cuối từ local state.

Từ gốc repo: `npm --prefix frontend ci`, `npm --prefix frontend run dev`. Vite proxy `/api` về backend localhost:8000; đổi `API_PROXY_TARGET` nếu dùng cổng riêng. CORS origins backend phải khớp origin thực.

Các scripts contracts:check/typecheck/lint/format:check/test/build phải đạt. ReviewPanel tests kiểm explicit null, conflict và archived read-only; kiểm tra browser thực được ghi ở [báo cáo](../docs/reports/product-verification-2026-10-24.md).
