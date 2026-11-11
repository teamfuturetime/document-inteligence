# Hướng dẫn làm việc trong repository

## Git và commit

- Commit thường xuyên theo từng thay đổi nhỏ, độc lập và có ý nghĩa. Một tính
  năng nhỏ, một bug fix, một phần kiểm thử, hay một cập nhật tài liệu đều có
  thể là một commit riêng khi đã hoàn chỉnh và kiểm tra được.
- Với công việc nhiều bước, hãy commit từng phần đã hoàn tất thay vì chờ cả
  công việc lớn mới commit. Không tạo commit chỉ để ghi nhận tiến độ dở dang,
  commit rỗng, hoặc chia một thay đổi nguyên tử thành các commit khó dùng riêng.
- Khi người dùng giao thực hiện một công việc, mặc định commit các phần thuộc
  đúng công việc đó sau khi hoàn tất. Không đưa thay đổi có sẵn, file ngoài
  phạm vi, hoặc nội dung do người khác tạo vào commit.
- Dùng Conventional Commits, ví dụ:
  - `feat(web): add document sample picker`
  - `fix(ocr): reject unsupported image format`
  - `test(api): cover empty extraction fields`
  - `docs(solo): explain local setup`
- Trước mỗi commit, xem `git status` và diff; stage đường dẫn cụ thể, rồi xem
  `git diff --cached --check` và `git diff --cached`. Không dùng `git add .`
  hoặc `git add -A` một cách thiếu kiểm soát.
- Không commit secret, `.env`, dữ liệu nhạy cảm, dependency folder hay artifact
  được sinh tự động nếu không cần thiết cho dự án.
- Không amend, rebase, reset, force push hoặc xóa lịch sử nếu chưa được yêu cầu.
  Việc người dùng yêu cầu commit không đồng nghĩa với cho phép push hoặc merge;
  chỉ push/merge khi có chỉ dẫn hoặc ủy quyền phù hợp.
- Sau khi commit, báo ngắn gọn commit hash, nội dung thay đổi và kiểm tra đã
  chạy. Nếu chưa thể commit an toàn, nêu rõ phần nào còn dang dở và lý do.

## Quy ước nhánh

- Dùng GitHub Flow với `main` ổn định và nhánh ngắn hạn như
  `feat/<ten-tinh-nang>`, `fix/<ten-loi>`, `docs/<chu-de>`, `test/<chu-de>`
  hoặc `chore/<chu-de>`.
- Không tự ý merge vào `main`. Giữ mỗi nhánh gắn với một mục tiêu cụ thể.

## Kiểm tra thay đổi

- Chạy các kiểm tra phù hợp với phần mã vừa sửa trước khi commit; không chạy
  lại bộ kiểm tra rộng nếu không có thay đổi hoặc lỗi mới cần xác minh.
- Không tuyên bố kiểm tra đã đạt nếu chưa chạy hoặc chưa thấy kết quả.
