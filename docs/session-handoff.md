# Bàn giao phiên — 21/10/2026 (Asia/Saigon)

## Task và Git

- Đóng phiên sau S3.1 và đưa tiến độ lên GitHub; không bắt đầu S3.2.
- Repository: `E:\HUS\subject\Code\SE\PROJECT\document-inteligence`.
- Branch: `tuannguyen`.
- HEAD lúc kiểm tra trước khi tạo bản bàn giao:
  `d6203429cd8c6c8c613392c97f2fbac6bcf744d8` —
  `feat: define extraction pipeline contract`.
- Khi bắt đầu bàn giao: working tree sạch, không có file mới/staged hoặc code dở;
  local và `origin/tuannguyen` cùng HEAD (ahead 0, behind 0).
- Lượt đóng phiên chỉ thêm file này bằng commit tài liệu local; không push.
  HEAD sau bàn giao xem bằng `git log -1 --oneline`; commit tài liệu sẽ đứng sau
  `d620342`, dự kiến ahead 1 so với remote đã kiểm tra. Xác minh lại ở phiên sau.

## Đã hoàn thành và xác minh

- S3.1 có Protocol provider, input ID/MIME/bytes, output thô/metadata và kết quả
  success/failure. Pipeline dùng lại normalization/business validation S2.2 và
  `InvoiceValues`; giữ nguyên `sales_invoice` 1.0.0, health-check và frontend.
- Fake offline có bốn scenario: complete, partial, failure, timeout; có nhãn/version,
  confidence null, evidence rỗng. Success không đồng nghĩa validation.valid hoặc
  dữ liệu đã được người dùng duyệt. Bổ sung 49 test, không thêm dependency.
- Đã push 8 commit tiến độ từ `1a7ad59` đến `d620342` bằng
  `git push -u origin tuannguyen`. Git xác nhận tạo branch và upstream thành công.
  `git ls-remote --heads origin tuannguyen main` xác nhận remote tuannguyen đúng
  `d620342`; main giữ `94c5101b94a43f1b0e2814d1cdfeee4139289673`.
- Đã rà 38 file tracked và quét 69 blob trong lịch sử HEAD bằng các mẫu secret:
  không phát hiện secret hoặc file môi trường/cache/build bị theo dõi. Chuỗi
  `DO_NOT_EXPOSE` là sentinel test tổng hợp; quét mẫu không bảo đảm phát hiện mọi secret.
  `.gitignore` loại `.env`, `.venv`, node_modules, cache và build output.

## Lệnh kiểm tra và kết quả thực tế

- `git fetch origin`: thành công trước push; remote chưa có tuannguyen lúc đó.
- `.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q`:
  lần gần nhất trước bàn giao **419 passed in 0.92s**, không warning.
- `git diff --check`, `git diff --cached --check`: đạt khi đóng phiên.
- `git rev-list --left-right --count HEAD...origin/tuannguyen`: `0 0`
  trước commit tài liệu bàn giao; `git status --porcelain=v1`: rỗng lúc đó.
- Backend chưa cấu hình type checker/linter. Không chạy lại backend/frontend tests
  trong lượt chỉ viết tài liệu bàn giao này.

## Dang dở, lỗi và giới hạn

- Không có code dở hoặc lỗi test/push chưa xử lý. Kết nối GitHub trong sandbox từng
  bị chặn; chạy lại lệnh Git với quyền mạng được cấp đã thành công, không đổi remote.
- S3.2 chưa bắt đầu; chưa chọn/đo OCR thật, chưa có VLM, upload, review hoặc export.
- Fake không giải mã ảnh; timeout là lỗi giả lập/truyền lỗi, chưa có deadline cưỡng chế.
  ExtractionResult đầy đủ và confidence có cơ sở thực nghiệm vẫn chưa triển khai.
- Frontend chưa được kiểm tra trực quan; CLI/HTTP/render trước đây không thay thế việc đó.

## Tiếp tục ở phiên sau

1. Đọc bản bàn giao; kiểm tra branch, HEAD, status và diff, đối chiếu roadmap.
   Không ghi đè thay đổi mới; commit bàn giao local chưa được push.
2. Task tiếp theo duy nhất theo roadmap: **S3.2 — OCR thật trên ảnh mẫu tổng hợp**.
   Chỉ triển khai khi phiên sau giao task này; không làm lại S3.1 hoặc mở rộng sang VLM/UI.
3. Giữ Conventional Commits; không push/merge/reset/amend nếu chưa có yêu cầu mới.

Đọc trước: [README](../README.md), [requirements](requirements.md),
[architecture](architecture.md), [roadmap](roadmap.md), [testing](testing.md) và
`..\MASTER_PROMPT_AI02_Solo_Development.md` (nằm ngoài repo).
Code liên quan: `backend/app/schemas/{invoice,extraction,validation}.py`,
`backend/app/providers/{contracts,fake}.py`,
`backend/app/services/{pipeline,normalization,validation}.py`,
`backend/tests/test_pipeline.py` và các test schema/service hiện có.
