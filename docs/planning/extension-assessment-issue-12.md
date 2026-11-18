# Đánh giá mở rộng OCR trước khi tích hợp — #12

Đề xuất cho [#12](https://github.com/teamfuturetime/document-inteligence/issues/12), dựa trên nền hóa đơn và đơn đề nghị tại `main@921541d`. Căn cứ phân loại theo đọc mã nguồn, test và tài liệu của nhánh gốc. Lượt này không chạy lại engine bên ngoài, gọi dịch vụ hoặc tải model.

| Phương án | Bằng chứng hiện có và điểm lệch nền | Đề xuất |
| --- | --- | --- |
| Chính sách hóa đơn | [VT-045 tại 69106d4](https://github.com/teamfuturetime/document-inteligence/tree/69106d4/backend) có policy JSON `invoice-policy-1`, loader strict/fail-closed và test riêng. Đó là workflow stateless. Nền docintel có `hoa_don`, integer VND và ràng buộc an toàn cho JSON. | Ưu tiên trước nếu nhóm thực sự cần cấu hình mức trần. Port loader/ý tưởng và tests vào domain hiện có, không mang schema khác. |
| Đơn sinh viên | [Solo tại c884a0b](https://github.com/teamfuturetime/document-inteligence/blob/c884a0b/solo/backend/src/ai02_solo/contracts.py) có schema `application`, aliases, rules và bộ mẫu riêng. Nền đã có `don_de_nghi`; tên trường, required fields và validation cần đối chiếu. | Map từng trường và thử trên bộ dữ liệu riêng trước. Giữ schema hiện tại nếu chỉ khác alias/bố cục. |
| CCCD | [Thao tại 760ccdc](https://github.com/teamfuturetime/document-inteligence/tree/760ccdc/ai_service) có rules/classification cho `cccd`; [Trí tại 66074f4](https://github.com/teamfuturetime/document-inteligence/tree/66074f4/ai_service) dùng `identity_card` và tập trường khác. Có implementation để tham khảo, chưa có kết quả nghiệm thu trên docintel. | Hoãn đến khi có nhu cầu và schema được duyệt. Chỉ tạo tài liệu hư cấu, tránh thông tin nhận dạng thật. |
| OCR.space | [Tài liệu solo tại c884a0b](https://github.com/teamfuturetime/document-inteligence/blob/c884a0b/solo/docs/ocrspace.md) ghi thử API thật trên synthetic trong app solo. Khác provider, hình thức gửi ảnh, giới hạn và mapping evidence. | Hoãn. Cần đặc tả dữ liệu được quyền gửi, quota/chi phí, key backend và đánh giá tách riêng. CI PR dùng test transport offline. |
| VLM local hoặc API | [Tài liệu solo tại c884a0b](https://github.com/teamfuturetime/document-inteligence/blob/c884a0b/solo/docs/vlm.md) có adapter và kiểm thử transport giả lập. Chưa có kết quả model thật trên các ca nền. | Hoãn đến khi có giả thuyết lỗi và ngân sách cho phép. Chọn một provider, pin model/prompt/schema, đo riêng OCR+rules và VLM. |

## Phạm vi đề nghị nếu nhóm duyệt một đợt triển khai

**Policy hóa đơn local là lát cắt đầu tiên.** Tách thành task riêng sau khi xác nhận nhu cầu cấu hình mức trần. Phác thảo acceptance:

1. Dùng `hoa_don` và validator backend làm nguồn chuẩn. Policy bất biến theo lần đánh giá, có version/hash và trần nguyên VND trong miền JSON an toàn. Không áp rule hóa đơn cho đơn đề nghị.
2. Trước khi ghi bất cứ cấu hình mới vào runtime, chốt nghĩa của policy đối với draft đã lưu, revision đã xác nhận và JSON lịch sử. Đề xuất giữ export hợp lệ đã xác nhận theo policy tại thời điểm confirm; lần confirm mới dùng policy hiện hành. Nếu cần persist policy ID theo revision, mở migration/contract task và bổ sung kiểm thử nâng cấp dữ liệu.
3. Bộ tests gồm đúng trần/vượt trần, config sai kiểu/thiếu/duplicate keys, ngày không hợp lệ, explicit-null, retry và restart; so trước/sau trên cùng quy trình. Policy lỗi cần báo rõ, không âm thầm dùng mặc định.
4. Với parser/OCR không đổi, đánh giá chính là mapping contract và validation. Nếu rule extraction thay đổi, lập bộ synthetic riêng theo loại, giữ splits theo parent/layout, report field-level/support/errors và confidence/abstention. Giữ provenance nguồn, quyền sử dụng, phiên bản schema/validation, engine/config và giới hạn mẫu. Không dùng điểm hóa đơn cho CCCD hoặc đơn sinh viên.

Điều kiện bàn giao cho mọi đề xuất đã được chọn: một adapter trong nền chung, không gộp ứng dụng khác, không thêm secret vào PR, test local/native upload → review → confirm → export cho hóa đơn và đơn đề nghị còn đạt. Khi schema contract đổi, tăng version, sinh lại OpenAPI/types/examples và chạy roundtrip revision/export.

## Quyết định còn cần nhóm chốt

- Có cần policy cấu hình thực tế hay giữ trần an toàn đang có?
- Nếu chọn policy, approval của ai quyết định version và tác động lên confirmed revisions?
- Các hướng tài liệu và provider khác để backlog đến khi có nhu cầu, dataset và phương án kiểm chứng độc lập.
