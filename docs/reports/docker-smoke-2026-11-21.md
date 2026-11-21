# Docker Compose smoke trên Windows — Issue #52

Thực hiện ngày 20–21/11/2026 (Asia/Saigon), tài khoản `tuanqtb123-creator`, Codex hỗ trợ.
Main nền `4191dfeb91a6b929784e8c5c9c30c45b0a83a029` đã tích hợp PR #27 và #66.
Nhánh `test/52-docker-smoke`, commit code `4a35ca74f3a485e329a77ec9b685f3279302ba8c`.
Head cuối cùng và kết quả Product CI được ghi trên PR hướng vào main.

## Môi trường và bằng chứng

Windows x64 build 26200.9711, WSL2 backend `docker-desktop`. Docker Desktop đã cài
được khởi động bằng `docker desktop start`. Lượt tiếp tục ngày 21/11 dùng Desktop
4.99.0.245822, Docker CLI/Engine 29.9.3, Compose 5.7.0, Linux/amd64 containers.
Lượt đầu ngày 20/11 ghi CLI/Engine 29.4.2 và Compose 5.1.3. Phiên QA không cài hoặc
đổi Docker settings. Lần kiểm dung lượng đầu ghi ổ C còn khoảng 31 GiB, E 120 GiB,
RAM 32 GiB và 18 logical processors.

Host dùng Python 3.14.5, uv 0.12.22, Node 24.16.0, npm 11.13.0 trong toolchain local
đã có. Docker build dùng Python 3.14.5-slim, uv 0.12.22, Node 24.16.0-alpine,
Nginx 1.28.0-alpine và lockfiles của repo. OCR trong container là Tesseract 5.5.0,
model revision `87416418657359cb625c412a48b6e1d6d41c29bd`, cả hai SHA-256 khớp lock.
Metadata đầy đủ và các document/run/revision/hash nằm trong
[evidence](../evidence/docker-smoke-2026-11-21.json).

Evidence ghi `head` tại lúc chạy bằng baseline Git khi source còn chưa commit.
`source_hashes` ghi bytes thực sự dùng cho build/probe. Đã đối chiếu các hash này
với working tree trước commit code nêu trên. Báo cáo không thay metadata Git null
trong container do build context đã loại `.git`.

## Kết quả thực thi

| Kiểm tra | Kết quả và phạm vi |
| --- | --- |
| Build backend/frontend | PASS với Dockerfiles đã sửa, dependencies theo locks, models tải và kiểm hash trong build |
| Startup và proxy | PASS containers healthy, readiness 200 và capabilities OCR ready qua Nginx. Chỉ frontend có cổng host loopback động, backend chỉ trên mạng project |
| PNG/JPEG native | PASS hai ảnh synthetic, run succeeded, prediction source model, có spans, input hash khớp bytes upload và models metadata khớp lock |
| Review/null/confirm/export | PASS reviewed null đọc lại vẫn null, confirm null bị từ chối 422, draft export bị từ chối 409. Review hợp lệ được confirm và export đúng revision 3 |
| Restart cùng volume | PASS document/run/prediction/review/history bằng trước restart, preview hash giữ nguyên và JSON export đúng dữ liệu đã xác nhận |
| Backup/restore | PASS manifest1 và mọi hash, SQLite integrity, source/preview và toàn bộ rows của documents/runs/revisions/events/users/sessions khớp. Runtime restore được khởi động và HTTP export vẫn đúng |
| Auth private state | PASS account/session synthetic tạo offline trong volume riêng được snapshot/restore, DB mode0600 và snapshot dir0700; profile HTTP được nghiệm thu ở local owner |
| Migration DB1→DB2 | PASS DB1 tạm tạo bằng migration SQL1 từ records synthetic vừa OCR. `migrate_runtime` tạo backup DB1 trước upgrade, giữ runs/revisions/events. Owner legacy vẫn local kể cả sau tạo tài khoản mới |
| Guards | PASS existing destination và dangling symlink bị từ chối ở backup/restore, không tạo target mất. Corrupt DB bị từ chối trước mkdir đích. Windows focused suites đã kiểm junction thật |
| Cleanup | PASS đúng project UUID, containers/network/volumes và image tags của project được dọn. Không có prune |
| `python scripts/dev.py check` | PASS từ lượt trước, 414 backend/pipeline +41 frontend, 29 contracts, data, Ruff/format, typecheck/lint/build, frozen replay30 và fixtures6. Logs còn nguyên |
| Focused migration/backup/restore/CLI | PASS 40 tests từ lượt trước |
| Guard tests mới của helper | PASS 3 tests, gồm deadline readiness và từ chối ghi đè report. Dùng transport doubles chỉ trong các unit tests này |
| `python scripts/dev.py doctor --json` | FAIL parser phiên bản Tesseract Windows 5.5.0.20241111 và runtime chẩn đoán chưa tạo. Theo dõi riêng #67 |
| Browser trong container | NOT RUN. Lượt Docker nghiệm thu HTTP thật qua frontend proxy |

Lệnh Docker cuối đã chạy:

```powershell
uv run --project backend --locked python scripts/check_docker_smoke.py --output runtime/issue-52/smoke-final.json
```

Logs local `runtime/issue-52/smoke-final.log`, report `smoke-final.json`,
`check.log`, `focused.log`, `doctor.log`. Bộ guard mới chạy bằng
`uv run --project backend --locked pytest backend/tests/test_docker_smoke.py -q -p no:cacheprovider`.
Các kiểm thử đầy đủ còn được chạy lại bởi Product CI ở head PR.

## Lỗi đã tái hiện và sửa

1. Build context gửi `backend/.pytest_cache` bị khóa quyền nên BuildKit báo Access denied.
   `.dockerignore` nay loại các cache pytest/Ruff/npm và browser result directories.
2. Frontend `npm run build` báo TS2307 khi test TypeScript import
   `contracts/examples/fixture-view.json`. Build stage nay copy contracts vào `/app/contracts`.
3. Backend healthy theo liveness nhưng OCR readiness503. Models được tải bằng root
   dưới mode0600, `docker exec` dưới user docintel đọc file báo PermissionError.
   Image nay đặt models công khai đã pin thành mode0644, user app giữ non-root.
4. Smoke cũ giữ cổng host động trước restart nên timeout. Helper nay đọc lại cổng
   sau restart/recreate, mỗi readiness request timeout2s trong tổng deadline90s.
   Assertion về cleanup và model pins đã chạy thành công ở lượt cuối.

Ba lỗi đóng gói nằm trong phạm vi sửa nhỏ của #52. Lượt smoke đầu thất bại readiness,
lượt hai thất bại ở địa chỉ cũ sau restart, lượt ba tạm dừng vì daemon chưa khởi động.
Hai lượt sau khi khởi động Docker và sửa helper đều PASS, không lấy các lượt thất bại
làm kết quả nghiệm thu thành công. Docker smoke không dùng inference double.

Snapshots có credential hashes/session state chỉ nằm trong volumes tạm đã cleanup.
Gold, splits, manifest, frozen evaluator và code publication chưa merge của #42/#43/#44
không tham gia thay đổi. Phạm vi là workflow trên synthetic PNG/JPEG, không suy ra
accuracy OCR ảnh thật hoặc hiệu năng production.
