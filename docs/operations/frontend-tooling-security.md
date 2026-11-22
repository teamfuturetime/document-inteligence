# Triage frontend tooling — issue #39

Đối chiếu ngày 22/11/2026 trên `main@692a834abef805066616a61af847af702ec698da`,
macOS arm64, Node **24.16.0** và npm **11.13.0**, clean install bằng package-lock.
Đây là snapshot dependency triage, không là security audit hoặc cam kết public-ready.

## Kết luận và thay đổi được chọn

[GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf)
đã được GitHub đánh dấu withdrawn ngày 18/11/2026, với lý do không phải security issue.
Trang advisory cập nhật ngày 19/11; patched versions vẫn là None, không có bản vá được
công bố trong advisory này. [Trao đổi upstream #235](https://github.com/micromatch/picomatch/pull/235)
đã đóng; maintainer khuyến cáo không cho nguồn không tin cậy định nghĩa glob/regex.
Không lấy bản vá đề xuất trong PR đã đóng làm release đã được hỗ trợ.

Clean audit hiện tại trả **0 full / 0 production vulnerabilities** với **picomatch 4.0.7
vẫn giữ nguyên trong lockfile**. Vì vậy kết quả khác báo cáo 12 affected packages mức high
ở issue #39 ngày 18/11 là trạng thái advisory/feed thay đổi, không phải repo đã nâng cấp
hoặc đã thực hiện một bản vá. Không sửa lại số liệu lịch sử thành kết quả hôm nay.

Giữ package.json, package-lock, runtime pins và semantics glob hiện có; không chạy
`audit fix --force`, thêm override hoặc downgrade Vite/Vitest chỉ để làm số audit giảm.
Đầu ra của issue chuyển thành quyết định triage có kiểm chứng; không cần thay dependency
khi advisory đã withdrawn và không có finding còn hoạt động trong snapshot.

## Dependency paths và input boundary

`npm --prefix frontend ls picomatch --all` tại checkout đã cài cho thấy:

| Đường phụ thuộc | Versions |
|---|---|
| Vite → picomatch | Vite 8.3.6 → picomatch 4.0.7 |
| Vite → tinyglobby → picomatch | tinyglobby 0.2.17 → picomatch 4.0.7 |
| Vite → tinyglobby → fdir → picomatch | fdir 6.5.0 → picomatch 4.0.7 |
| Vitest → picomatch | Vitest 5.0.3 → picomatch 4.0.7 |

Đã đọc các call sites cài từ lock: Vite imports picomatch/tinyglobby trong node chunks,
Vitest dùng chúng để chọn test/module paths, tinyglobby biên dịch patterns thành matchers
và fdir dùng picomatch khi globbing. Trong repo, `frontend/vite.config.ts` dùng test excludes
cố định và Vite proxy loopback; `frontend/eslint.config.js` có ignores cố định. Frontend
production chỉ khai báo React/react-dom; `frontend/src` không import glob/picomatch hoặc
nhận glob pattern do người dùng nhập. Upload đi qua API backend, không qua glob matcher.

Từ các call sites đã đọc, input pattern thuộc code/config/CLI của người phát triển.
Đây là đánh giá phạm vi của repo hiện tại, không chứng minh mọi plugin/cấu hình tương lai
an toàn. Không chạy toolchain trên PR/config không tin cậy kèm secrets/quyền cao, và không
thêm endpoint hay giao diện chuyển input người dùng thành regex/glob tùy ý. Nếu boundary
đổi hoặc có advisory mới, tái triage theo finding và version thực; audit production=0
không loại hết rủi ro tooling hay ứng dụng.

## Tái lập snapshot

Từ root với pins ở README, trong checkout sạch:

```sh
npm --prefix frontend ci
npm --prefix frontend audit --json
npm --prefix frontend audit --omit=dev --json
npm --prefix frontend ls picomatch --all
```

Cả hai lệnh audit đã chạy exit 0, `auditReportVersion=2`, vulnerabilities map rỗng và
mọi severity count bằng 0. Metadata dependency inventory: prod 4, dev 244, optional 27,
peer 8, total 247; các nhóm có thể chồng lắp, không cộng thành số packages đã cài.
`npm ci` thực cài 223 packages trên platform này, audit 224 packages.
SHA-256 package-lock tại lần kiểm:
`19647a05eeb0d93cad4b2ec6c0bac759335b83a5e22cc63401bbfc7b40f60501`.
Registry snapshot có thể thay đổi dù lock không đổi. Không lưu cache/node_modules hoặc
raw environment/logs vào Git; commands trên là cách kiểm lại trạng thái mới.

Không có code/dependency thay đổi trong task này nên không tạo test mô phỏng advisory
hoặc ép sửa expected tests. Repository checker/diff và full Product CI của PR vẫn là
điều kiện tích hợp; kết quả cùng SHA được ghi trên PR, không lấy CI nhánh khác để tự đóng #39.
