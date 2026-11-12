# Đặc tả yêu cầu

Mục tiêu nghiệp vụ: giảm công nhập liệu trong khi người dùng kiểm soát sai sót trước khi sử dụng dữ liệu. Actor: người dùng demo local và nhóm phát triển/QA. Foundation không có danh tính thật hay cộng tác nhiều người trong ứng dụng.

| ID | Yêu cầu chức năng và điều kiện chấp nhận mục tiêu |
| --- | --- |
| MVP-01 | OCR giữ spans, text, page, tọa độ/kích thước ảnh, metadata engine/weights; lỗi unavailable không fallback mock |
| MVP-02 | Ánh xạ theo schema, giữ raw/normalized/evidence, nhiều ứng viên có thể abstain; không đọc gold |
| MVP-03 | Confidence theo trường có method/policy/reasons, unknown khi thiếu tín hiệu; công bố calibration chỉ có dữ liệu chứng minh |
| MVP-04 | Ảnh cạnh form, sửa/lưu bản nháp, ghi revision/sự kiện, xác nhận explicit; không ghi đè prediction |
| MVP-05 | Validation cấu trúc, ngày thực sự tồn tại, chuỗi mã số, liên trường; issue code/path/severity/message; draft cho phép thiếu/sai |
| MVP-06 | Backend xuất revision đã lưu, confirmed, hợp lệ; không tin JSON hoặc cờ approved do frontend gửi |
| DATA-01 | Chỉ synthetic/sample có nguồn gốc và quyền sử dụng phù hợp |
| EVD-01..04 | Golden dataset; metrics trước review; error taxonomy; model/config/run truy vết |
| ENG-01..04 | Cài lại bằng lock; issue/PR workflow; kiểm thử/CI không che lỗi; capabilities và UI phản ánh tình trạng thật |

Schema provisional `don_de_nghi@1.0.0` yêu cầu 7 trường khi xuất: full_name, student_id, date_of_birth, class_name, faculty, request_content, request_date. Quy tắc student_id là chuỗi chữ số ASCII, không định độ dài nghiệp vụ trước BL-001. Ngày input dd/mm/yyyy được hiểu theo schema Việt Nam; normalized là ISO date; không đoán ngày mơ hồ. Ngày sinh không sau ngày làm đơn.

## Phi chức năng

| ID | Tiêu chí đo/kiểm tra | Tình trạng |
| --- | --- | --- |
| NFR-01 | Cài frozen lock, tests/build/contracts check bằng lệnh README không cần API key/GPU | Kiểm tra foundation tại báo cáo |
| NFR-02 | Modules có ranh giới; evaluator không import frontend hoặc khởi động server | Implemented |
| NFR-03 | UI có label, keyboard focus, giải thích chữ cho confidence, loading/error/empty | Foundation UI; UX review đầy đủ planned |
| NFR-04 | PNG/JPG, một trang, 5 MiB, 16 triệu pixel, timeout provider 30 giây | Config provisional; upload/provider enforcement chưa có |
| NFR-05 | Thời gian xử lý, latency cold/warm, khả dụng và mức tiết kiệm nhập liệu | TBD sau baseline; chưa đo |
| NFR-06 | Chi phí API/giới hạn retry/quota; không phát sinh phí dựng nền | Ngân sách TBD; không gọi API AI |
| NFR-07 | Không secret/PII/runtime DB trong Git; bind local, escape output, safe fixture paths | Bảo vệ áp dụng chức năng hiện có |

Thay đổi phạm vi/schema dùng ADR và cập nhật [traceability](traceability.md), examples, versions, tests. Không có threshold chất lượng tự đặt để khóa merge từ fixture.
