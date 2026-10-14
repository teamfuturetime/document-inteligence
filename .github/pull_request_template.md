## Vấn đề và kết quả

Mô tả hành vi trước/sau hoặc kết quả tài liệu/cấu hình.
Closes #... (thay bằng số issue thật; bỏ dòng nếu chưa có issue).

## Phạm vi thay đổi

File/module và quyết định kỹ thuật cần reviewer biết:

## Test evidence

Lệnh/kịch bản thực sự đã chạy + kết quả. Link CI run và commit SHA nếu đã có.
Ghi rõ checks chưa chạy và lý do; local pass không đồng nghĩa GitHub CI pass.

## Trạng thái triển khai

Real / mock / chưa triển khai; hạn chế hoặc contract thay đổi:

## Review checklist

- [ ] Thay đổi nằm trong phạm vi issue.
- [ ] Đã review staged diff; không secret/PII/dependency/generated artifact.
- [ ] Tests/verification phù hợp đã chạy và evidence ở trên.
- [ ] Docs/schema/version được cập nhật nếu cần.
- [ ] Có reviewer khác tác giả; contract đã được owner liên quan review.
- [ ] `Backend checks` và `Frontend checks` pass trên đúng commit trước merge.
