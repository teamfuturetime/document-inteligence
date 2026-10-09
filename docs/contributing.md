# Quy trình Git và GitHub

## GitHub Flow

`main` ổn định. Mỗi issue dùng branch ngắn hạn: `feat/<feature>`, `fix/<bug>`,
`docs/<topic>`, `test/<topic>`, `chore/<topic>`, `refactor/<topic>`.
Không thêm `develop` dài hạn. Mở draft PR sớm để thống nhất interface.
Một PR giải quyết một issue/phạm vi; có thể chứa nhiều atomic commit.

Mỗi người chịu trách nhiệm branch của mình. Đồng bộ main bằng merge thông
thường nếu cần; không tự amend/rebase/reset/force push hoặc viết lại lịch sử.
Nếu conflict, đọc cả hai thay đổi, trao đổi owner, sửa và chạy kiểm tra liên quan.
Không ghi đè hoặc stage thay đổi của người khác khi chưa có sự đồng ý.

## Một task từ đầu tới cuối

Các lệnh dưới đây là hướng dẫn cho người thực hiện. Push/merge chỉ được thực
hiện khi người dùng/nhóm cho phép; agent không tự chạy theo ví dụ tài liệu.

```bash
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feat/invoice-validation
# Chỉnh đúng phạm vi issue, chạy test phù hợp rồi review diff.
git diff --check
git diff -- backend/app/models/invoice.py backend/tests/test_invoice.py
git add backend/app/models/invoice.py backend/tests/test_invoice.py
git status --short
git diff --cached --check
git diff --cached
git commit -m "feat(validation): validate invoice date and amount"
# Khi đã được phép publish:
git push -u origin feat/invoice-validation
```

File trong ví dụ validation chưa tồn tại ở Phase 0. Nếu đang có thay đổi local,
không switch/pull mù quáng. `pull --ff-only` thất bại thì kiểm tra divergence,
không dùng reset để ép branch khớp remote.

Conventional Commits: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`;
scope theo module nếu hữu ích. Một commit là một thay đổi logic có thể review.
Test đi cùng feature/fix khi cần chứng minh hành vi; không tách commit để tạo
lịch sử có code lỗi. Không dùng `git add .` tùy tiện; kiểm tra mọi staged file.

Trước commit: liệt kê file/mục đích, kiểm tra status và cached diff, chạy test
thực tế, ghi rõ checks chưa chạy. Không commit secret, `.env`, dữ liệu thật,
dependency folders hoặc generated reports. Lockfile phải được commit khi có.

## Pull request và bảo vệ main

PR ghi vấn đề/hành vi mới, `Closes #<issue>` khi có số thật, phạm vi file,
test evidence gồm lệnh/kết quả, và limitations/mock status. Chọn tối thiểu một
reviewer khác tác giả; thay đổi contract cần Backend + Frontend/Extraction review.
CI phải pass trước merge. Trong Phase 0 chưa có CI ứng dụng, dùng evidence kiểm
tra tài liệu thủ công; Phase 2 thêm checks thật và chọn chúng làm required.

Admin nên cấu hình main yêu cầu PR + một approval, cấm force push, yêu cầu
resolve discussions và required CI checks sau P2-04. Đây là đề xuất, chưa
cấu hình GitHub. Merge thường giữ atomic history; không squash mặc định nếu
nhóm muốn giữ từng checkpoint. Chỉ người được nhóm phân quyền thực hiện merge.

## Task đầu tiên trên repository thực tế

Repo không hoàn toàn trống: đã có `94c5101 first commit` và README một dòng.
Working tree ban đầu sạch; remote `origin` trỏ tới repository nhóm.
Đã giữ commit cũ và tạo branch `chore/project-bootstrap`.

P0-01 có hai file: README root xác định MVP/trạng thái, `.gitignore` bảo vệ
secret/dependency/artifact. Verification: diff whitespace và ignore rules.
Các lệnh thực hiện:

```bash
git switch -c chore/project-bootstrap
git diff --check
git check-ignore .env .env.local backend/.venv/a frontend/node_modules/a
git check-ignore data/uploads/a evaluation/reports/a
git check-ignore .env.example frontend/package-lock.json data/samples/invoice.json
# Lệnh cuối cần không có output và exit 1: các file này KHÔNG bị ignore.
git add README.md .gitignore
git status --short
git diff --cached --check
git diff --cached
git commit -m "chore: initialize project overview and ignore rules"
```

Đây là bản ghi task đã thực hiện, không chạy lại lệnh tạo branch khi đang ở
branch đó. P0-02 thêm kiến trúc + README các module; P0-03 thêm roadmap/issues;
P0-04 thêm tài liệu này và templates. Danh sách file/commit xem bằng:

```bash
git log --oneline main..HEAD
git diff --stat main...HEAD
git show --stat HEAD
git status --short
```

Sau review Phase 0, task kế tiếp là P1-01 chốt phạm vi; sau đó P1-02 schema/API
và P1-03 synthetic samples. Không khởi tạo app trước khi contract được chốt.
