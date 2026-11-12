# Dependency triage — issue #9

Snapshot ngày 12/11/2026 (Asia/Ho_Chi_Minh), nền main `0868cf6`. Nguồn dependency: frontend/package-lock.json SHA256 `3901eb8ee1b983404053c0150f73eb8b94900463f938dcfae0cffff63a2c8d36`.

## Phát hiện ban đầu

`npm --prefix frontend audit --json` báo 10 mục moderate, 0 high/critical. Đây là 10 package nodes chịu ảnh hưởng, không phải 10 lỗ hổng độc lập. Một advisory gốc: [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249), minimatch globparts amplification, range >=7.0.0 <11.0.1. Lock đang giải minimatch 10.2.6.

| Đường dependency | Phạm vi dùng trong repo |
|---|---|
| eslint → minimatch | Lựa chọn file khi lint |
| eslint → @eslint/config-array → minimatch | files/ignores của flat config |
| typescript-eslint → parser/plugin/utils → typescript-estree → minimatch | Bộ parser và project-service matching khi được cấu hình |

Các package này đều là dev tooling, không phải dependency runtime của React app. Audit `--omit=dev` hiện báo 0 vulnerabilities; không có nghĩa mọi công cụ build hoặc CI đều an toàn tuyệt đối. Rủi ro là DoS trong môi trường tooling khi xử lý pattern không tin cậy, không có bằng chứng đây là đường tấn công qua file hóa đơn trên backend. CI PR vẫn thực thi code chưa tin cậy; không coi phân loại dev là lý do bỏ qua advisory.

Raw snapshots và metadata registry: [audit trước](../evidence/dependency-audit-2026-11-12/audit-before.json), [runtime trước](../evidence/dependency-audit-2026-11-12/production-before.json), [ESLint mới nhất tại lúc khảo sát](../evidence/dependency-audit-2026-11-12/eslint-metadata.json), [typescript-estree mới nhất](../evidence/dependency-audit-2026-11-12/typescript-estree-metadata.json), [minimatch 11.0.8](../evidence/dependency-audit-2026-11-12/minimatch-metadata.json). Audit JSON không phải SBOM hoặc kiểm tra toàn bộ Python/Docker dependencies.

## Quyết định khắc phục

ESLint 10.14.0 và typescript-estree 8.72.2 tại lúc khảo sát vẫn khai báo minimatch major 10; chỉ nâng hai package này không giải quyết advisory. Không hạ ESLint về major 9 hoặc typescript-eslint cũ theo gợi ý audit; không dùng audit fix --force.

Thử override có giới hạn các bản minimatch thỏa `^10.2.2` sang bản cố định 11.0.8, giữ nguyên mọi direct dependency và runtime pins. Đây là major override cần review, không phải bản vá semver tự động được upstream bảo đảm. [Changelog minimatch](https://github.com/isaacs/minimatch/blob/main/changelog.md) ghi major 11 bỏ makeRe/AST, đổi phần tử set và một số matching semantics. Ba call sites trong dependencies cài từ lock hiện dùng Minimatch.match/pattern và minimatch(), không thấy gọi các API đã bỏ tại những call sites đó.

Trước khi chấp nhận override phải clean install với Node24.16.0/npm11.13.0, audit lại, kiểm tra cùng tập file lint trước/sau, contracts/typecheck/lint/format/component/build và native browser E2E. Ghi kết quả sau kiểm chứng; chưa suy tương thích trên Windows hoặc mọi tính năng tùy chọn của ESLint/typescript-eslint từ lint cấu hình hiện tại.

Khi upstream cho phép minimatch đã vá trong range chính thức, bỏ override và tạo lock bằng npm đã pin, chạy lại cùng kiểm tra. Không bỏ qua/allowlist advisory hoặc thay CI để làm xanh. Thay đổi ngoài dependency tooling không thuộc #9.

## Kết quả sau bản vá

Bản vá dependency tại commit `8229284`; lock sau SHA256 xem [verification](../evidence/dependency-audit-2026-11-12/verification.json). Direct dependencies, Python lock, runtime pins, mã sản phẩm và workflows giữ nguyên. Override chỉ áp major 10 thỏa range đã chọn; minimatch 5.1.9 trong openapi-typescript không bị ép major. [Dependency tree sau cài](../evidence/dependency-audit-2026-11-12/minimatch-tree.json) xác nhận ba consumers lint dùng 11.0.8.

| Kiểm tra local, Node24.16.0/npm11.13.0, macOS ARM64 | Kết quả |
|---|---|
| npm ci từ lock mới | Pass; tạo lại node_modules, không tái dùng dependency tree cũ |
| npm audit --json / --omit=dev --json | Cả hai 0 vulnerabilities tại lúc chụp |
| ESLint . --format json trước/sau | Đúng cùng 19 file, toàn bộ results JSON giống nhau; không giảm phạm vi lint |
| contracts:check, typecheck, lint, format:check | Pass |
| npm test | 12 tests / 3 files pass |
| npm run build | Pass |
| npm run test:e2e | 1 Chromium native OCR test pass; upload/null/reload/edit/conflict/confirm/download |

[Audit sau](../evidence/dependency-audit-2026-11-12/audit-after.json), [runtime sau](../evidence/dependency-audit-2026-11-12/production-after.json). Tesseract 5.5.2 với vie/eng tải bằng helper và SHA256 đã xác minh. E2E dùng backend/SQLite tạm của Playwright, không dùng DB người dùng. Đây là kiểm tra luồng có OCR thật, không phải benchmark chất lượng OCR mới.

Đã dùng clean npm install trong workspace hiện có, **không** tuyên bố đã chạy toàn bộ dự án trong checkout sạch: có artifacts local từ nhánh cũ ngoài phạm vi, không đưa vào commit. E2E khởi chạy trong lúc thay đổi dependency đang được commit; dependency files khớp `8229284`, không gọi đó là run từ working tree sạch. CI trên PR là bước kiểm tra checkout sạch/Linux tiếp theo. Chưa chạy Docker/Windows; không suy tính tương thích toàn bộ optional parser/project-service modes từ cấu hình hiện tại. Không có advisory đang báo còn lại trong npm snapshot này, nhưng override qua major là rủi ro cần reviewer chấp nhận.

## Tái kiểm tra và rollback

Dùng Node/npm theo pins của frontend, chạy từ root: `npm --prefix frontend ci`, `npm --prefix frontend audit --json`, `npm --prefix frontend audit --omit=dev --json`, rồi `python scripts/dev.py frontend-check` và `python scripts/dev.py e2e` theo README (models/browser cần có). Để so phạm vi lint, chạy `eslint . --format json` từ frontend trên nền và bản vá, so đường dẫn tương đối cùng messages/error/warning counts. Các audit JSON là snapshot theo thời điểm; không cam kết registry sẽ luôn báo 0.

Nếu reviewer phát hiện matching behavior cần API đã bỏ, revert commit dependency bằng commit/PR mới và giữ advisory được công bố, không allowlist che cảnh báo. Khi upstream hỗ trợ range đã vá, bỏ override, tạo lock mới bằng toolchain đã pin và lặp lại kiểm tra. Không tự merge PR này.
