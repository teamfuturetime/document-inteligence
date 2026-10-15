# Validation dữ liệu review — P4-02

`POST /api/v1/validate` nhận ValidationRequest v1.0.0 (năm string/null).
Trả HTTP 200 với `valid`, `normalized_values`, `errors`; wire input sai trả
422 `invalid_request`. Field sai được trả null; không làm mất field đúng.

Chuỗi NFC/trim/collapse whitespace; mã hóa đơn và tên bên bán theo baseline
extraction. Ngày review yêu cầu ISO YYYY-MM-DD, kiểm tra lịch thực. Tiền VND
integer không âm, safe integer JavaScript; nhóm nghìn/suffix theo normalization
đã khai báo trong extraction. Currency chỉ normalize aliases VND, không mặc định.
Thiếu trường báo `required`, định dạng sai `invalid_format`, ngày sai lịch
`invalid_date`, vượt miền `out_of_range`, ngoại tệ `unsupported_currency`.

Service không lưu dữ liệu hoặc thay confidence/evidence OCR. Frontend phải
vô hiệu hóa validation cũ sau mỗi edit và chỉ export khi validation hiện tại
đạt. [Phase 5](review-export.md) đã có luồng đó; [P4-03](real-pipeline.md) đã tích hợp extraction thật.

Verification: `python -m pytest backend/tests/test_review_validation.py -q`;
kiểm tra API thật bằng TestClient, leap date/zero/max/invalid types/Unicode.
