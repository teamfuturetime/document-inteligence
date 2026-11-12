## Vấn đề và hành vi thay đổi

Issue/CONS ID, trước → sau, phạm vi hóa đơn và phần mở rộng bị ảnh hưởng. Port từ đâu: branch/commit/author, phần giữ/chưa chuyển.

## Kiểm chứng trên đúng SHA

- `python scripts/dev.py check`: kết quả / chưa chạy + lý do
- `python scripts/dev.py ocr`: native hay doubles, engine/model/config/dataset/source SHA
- `python scripts/dev.py e2e`: browser/native result
- Thay domain/API/data/model: version/hash/schema/types và evaluation regression nào đã kiểm tra?

## Tương thích và rủi ro

API/schema/runtime/DB path có thay đổi không? Có cần backup/migration? Giữ null/CAS/history/server export/owner boundary ra sao? Giới hạn còn lại và rollback.

## Review

- [ ] Diff đã đọc; stage/commit chỉ thuộc task, không secret/PII/model/runtime/output cá nhân.
- [ ] Không sửa gold/threshold/expected để che regression.
- [ ] CI đúng head/merge SHA và mọi Product checks đều pass; không chỉ nhãn xanh của commit khác.
- [ ] README/docs hiện hành khớp implementation; báo cáo cũ được ghi là lịch sử.
- [ ] Một người khác review trước merge; chưa tự merge hoặc đổi quyền GitHub.
