# Risk register

Đánh giá định tính tạm thời, không xác suất số/thiệt hại giả. Owner là vai trò, người cụ thể TBD.

| Rủi ro | Probability/impact | Owner | Mitigation | Dấu hiệu hành động |
| --- | --- | --- | --- | --- |
| Loại tài liệu quá rộng | Trung bình/Cao | Điều phối | BL-001 chốt typed/schema/page; thêm scope bằng ADR | Yêu cầu nhiều mẫu/line items/chữ viết tay chưa có contract |
| OCR Việt kém | Trung bình/Cao | Backend | Spike engine/version trên ảnh được phép, phân chữ/layout | Dấu/mã/span sai lặp lại baseline |
| Render/gold sai | Trung bình/Cao | Data/QA | Đối chiếu ảnh/gold, font hash/tràn, review chéo | Glyph mất dấu/crop tràn/labels không còn thấy |
| Split leakage | Trung bình/Cao | Data/QA | Parent grouping/checksum/content/template audit | Parent/hashes/content qua nhiều split |
| API model cost/quota/mạng | Chưa biết/Cao | Backend + điều phối | Không gọi dựng nền; budget/timeout/retry/config/snapshot khi chọn | Timeout/quota/cost khác kế hoạch |
| Confidence hiểu nhầm | Trung bình/Cao | Frontend + QA | Unknown/heuristic bằng chữ, validation calibration, support | UI/số liệu gọi score là probability chưa chứng minh |
| Save/export sai revision | Trung bình/Cao | Backend + frontend | Persisted latest/confirmed/valid gates, 409/E2E/clear-null | Mất sửa, xuất stale, xác nhận từ flag client |
| Thành viên không chạy được | Trung bình/Trung bình | Điều phối + QA | Pins/locks/onboarding/troubleshooting, Docker verify khi có | Install/build không khớp môi trường báo cáo |
| Thư viện/model thay đổi | Trung bình/Trung bình | Backend + QA | Exact locks/package vs weights hash, ADR upgrade, checks | Dependency không hỗ trợ runtime/snapshot đổi |

Revisit khi spike/benchmark/nguồn lực có evidence; bổ sung issue thật theo trigger, không suy ra thành viên hoặc ngày chưa có.
