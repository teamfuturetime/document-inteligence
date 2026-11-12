# Hướng dẫn cho coding agents

- Đọc [scope](docs/requirements/scope.md), [contracts](contracts/README.md) và ADR liên quan trước khi sửa; giữ requirement IDs và ranh giới FOUNDATION/PRODUCT_MVP.
- Kế thừa mã và thay đổi của người khác; không reset, đổi remote, force-push hoặc bịa đóng góp.
- Backend domain models là nguồn chuẩn. Đổi schema/API phải cập nhật version, generated contracts, frontend types, examples và tests; không sửa bản sinh bằng tay.
- Giữ prediction máy riêng với review. `is_reviewed=true` và `reviewed_value=null` là người dùng xóa, không fallback bằng toán tử `or`.
- Inference không đọc gold. Fixture phải bật rõ, không fallback khi provider lỗi; fixture metrics không phải benchmark. Không tối ưu trên test rồi báo là phép đánh giá độc lập.
- Chỉ synthetic/sample hợp lệ; secrets, upload, DB/cache và model weights nằm ngoài Git. Không bịa confidence, metrics, model versions, test results, người tham gia hoặc tài khoản GitHub.
- Không sửa expected tests để che bug; chỉ đổi khi yêu cầu/contract đổi có lý do. Thay đổi data/model/config cập nhật versions, hashes và evidence.
- Kiểm tra backend/AI: `uv run --project backend --locked ruff check backend scripts pipeline`, `uv run --project backend --locked ruff format --check backend scripts pipeline`, `uv run --project backend --locked pytest backend/tests pipeline/tests -q`. Native workflow: `uv run --project backend --locked python scripts/verify_product.py`; cần Tesseract/models thật, không skip/fallback.
- Contracts/data: `uv run --project backend --locked python scripts/generate_contracts.py --check`, `uv run --project backend --locked python scripts/check_data.py`, `uv run --project backend --locked python scripts/evaluate_fixtures.py`, `uv run --project backend --locked python scripts/check_repository.py`.
- Frontend: `npm --prefix frontend run contracts:check`, `typecheck`, `lint`, `format:check`, `npm --prefix frontend test`, `npm --prefix frontend run build`; các tên ngắn trước đó là npm scripts.
- Báo rõ lệnh đã chạy, kết quả và pending checks. Không tự triển khai cloud, mua dịch vụ, gửi thông báo hoặc đổi quyền repository ngoài phạm vi được giao.

## Consolidation và Git

- README root/scripts/dev.py là nguồn lệnh chạy; ADR0008 là nền hiện hành. Một frontend/backend/pipeline, không tạo app cạnh tranh trong archive.
- GitHub Flow: main ổn định → feat/fix/docs/test/chore ngắn hạn → PR/checks/review. Nhánh cá nhân/bài tập là ref lịch sử; không xóa hoặc đổi link nộp.
- Commit phần nhỏ hoàn chỉnh theo Conventional Commits, review status/diff, stage paths cụ thể, kiểm staged diff/check. Không commit output cá nhân, runtime/models/DB/secrets.
- Không push, merge, force-push, rebase/amend/reset, đổi default branch/quyền hoặc xóa nhánh khi chưa có ủy quyền. Gói thao tác GitHub phải có nội dung cụ thể để người dùng duyệt trước.
