# Dependency triage — issue #9

Snapshot ngày 13/11/2026 (Asia/Ho_Chi_Minh), nền main `0868cf6`. Nguồn dependency: frontend/package-lock.json SHA256 `3901eb8ee1b983404053c0150f73eb8b94900463f938dcfae0cffff63a2c8d36`.

## Phát hiện ban đầu

`npm --prefix frontend audit --json` báo 10 mục moderate, 0 high/critical. Đây là 10 package nodes chịu ảnh hưởng, không phải 10 lỗ hổng độc lập. Một advisory gốc: [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249), minimatch globparts amplification, range >=7.0.0 <11.0.1. Lock đang giải minimatch 10.2.6.

| Đường dependency | Phạm vi dùng trong repo |
|---|---|
| eslint → minimatch | Lựa chọn file khi lint |
| eslint → @eslint/config-array → minimatch | files/ignores của flat config |
| typescript-eslint → parser/plugin/utils → typescript-estree → minimatch | Bộ parser và project-service matching khi được cấu hình |

Các package này đều là dev tooling, không phải dependency runtime của React app. Audit `--omit=dev` hiện báo 0 vulnerabilities; không có nghĩa mọi công cụ build hoặc CI đều an toàn tuyệt đối. Rủi ro là DoS trong môi trường tooling khi xử lý pattern không tin cậy, không có bằng chứng đây là đường tấn công qua file hóa đơn trên backend. CI PR vẫn thực thi code chưa tin cậy; không coi phân loại dev là lý do bỏ qua advisory.

Raw snapshots và metadata registry: [audit trước](../evidence/dependency-audit-2026-11-13/audit-before.json), [runtime trước](../evidence/dependency-audit-2026-11-13/production-before.json), [ESLint mới nhất tại lúc khảo sát](../evidence/dependency-audit-2026-11-13/eslint-metadata.json), [typescript-estree mới nhất](../evidence/dependency-audit-2026-11-13/typescript-estree-metadata.json), [minimatch 11.0.8](../evidence/dependency-audit-2026-11-13/minimatch-metadata.json). Audit JSON không phải SBOM hoặc kiểm tra toàn bộ Python/Docker dependencies.

## Quyết định khắc phục

ESLint 10.14.0 và typescript-estree 8.72.2 tại lúc khảo sát vẫn khai báo minimatch major 10; chỉ nâng hai package này không giải quyết advisory. Không hạ ESLint về major 9 hoặc typescript-eslint cũ theo gợi ý audit; không dùng audit fix --force.

Thử override có giới hạn các bản minimatch thỏa `^10.2.2` sang bản cố định 11.0.8, giữ nguyên mọi direct dependency và runtime pins. Đây là major override cần review, không phải bản vá semver tự động được upstream bảo đảm. [Changelog minimatch](https://github.com/isaacs/minimatch/blob/main/changelog.md) ghi major 11 bỏ makeRe/AST, đổi phần tử set và một số matching semantics. Ba call sites trong dependencies cài từ lock hiện dùng Minimatch.match/pattern và minimatch(), không thấy gọi các API đã bỏ tại những call sites đó.

Trước khi chấp nhận override phải clean install với Node24.16.0/npm11.13.0, audit lại, kiểm tra cùng tập file lint trước/sau, contracts/typecheck/lint/format/component/build và native browser E2E. Ghi kết quả sau kiểm chứng; chưa suy tương thích trên Windows hoặc mọi tính năng tùy chọn của ESLint/typescript-eslint từ lint cấu hình hiện tại.

Khi upstream cho phép minimatch đã vá trong range chính thức, bỏ override và tạo lock bằng npm đã pin, chạy lại cùng kiểm tra. Không bỏ qua/allowlist advisory hoặc thay CI để làm xanh. Thay đổi ngoài dependency tooling không thuộc #9.
