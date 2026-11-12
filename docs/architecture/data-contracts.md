# Hợp đồng dữ liệu

Nguồn chuẩn: Pydantic domain models strict types/extra forbid trong `backend/src/docintel/domain/models.py`; API models và FastAPI routes sinh OpenAPI. [Generated contracts](../../contracts/README.md) và frontend types không được chỉnh tay. Export schema `1.0.0` độc lập app `0.1.0`. Đổi field/type/required/semantics là breaking change: ADR, tăng major export/schema, migration nếu có persistence, cập nhật config/fixtures/tests/types/docs. Thêm tùy chọn tương thích dùng minor; sửa không đổi nghĩa dùng patch.

| Entity | Hợp đồng/trách nhiệm | Nền |
| --- | --- | --- |
| Document | ID/type/checksum/page/provenance | Model; chưa lưu upload |
| ExtractionRun | ID/document/schema/provenance/status/fields/spans | Fixture, prediction bất biến theo run ở MVP |
| OCRSpan | Text/page/score/polygon/image dimensions/coordinate convention | Fixture; điểm OCR null |
| FieldPrediction | Field ID/raw/normalized/observation/evidence/confidence | Fixture/model contract |
| ReviewRevision | Revision/status/ReviewedField/issues/saved_at | Contract; chưa lưu |
| ReviewEvent | old/new/action/time/reviewer_id optional | Contract; không bịa danh tính |
| ValidationIssue | code/field_path/severity/message | Chạy thật trên draft |
| ExportArtifact | type/schema/document/run/revision/data/confirmed/provenance | Ví dụ/schema; chưa có export service |

DraftApplicationData cho phép null/missing và string ngày sai, lưu kèm issues; FinalApplicationData bắt buộc 7 trường không trống, ngày ISO tồn tại, student_id string chữ số, ngày sinh không sau ngày đơn. JSON Schema kiểm tra cấu trúc/regex; quy tắc lịch/ngày liên trường cần Pydantic/validator, không suy diễn regex là lịch hợp lệ. Raw không sửa khi normalized/review thay đổi. Người dùng chủ động xóa có `is_reviewed=true, reviewed_value=null`; effective_value phải dựa flag.

Tọa độ: page_index **0-based**; UI hiển thị 1-based. Polygon bốn điểm trong pixel ảnh gốc, gốc top-left, x sang phải/y xuống, kèm image_width/height. Scaffold chỉ `transform=identity`; adapter sau crop/xoay cần mở contract/version và mapping về ảnh gốc. Không evidence thì polygon null, evidence_status unknown/unavailable, không bịa tọa độ. Run kiểm tra span ID/field ID không trùng và references tồn tại.

Gold: present có giá trị nhìn thấy; absent/unreadable null. Prediction: found có raw_value; not_found/unreadable/unknown cần null và không suy từ gold. Confidence method/policy_version/reason_codes; unknown score null. data_origin synthetic/sample độc lập prediction_source fixture/model/unavailable: model thật trên ảnh synthetic vẫn là synthetic + model.

Revision MVP: số tăng dần; edit confirmed tạo draft mới; lưu/confirm/export dùng expected_revision và từ chối stale bằng 409. Re-OCR tạo run mới, không ghi đè review. Export backend lấy revision persisted/latest/confirmed/validated; không tin payload dữ liệu cuối từ client. Không có cơ chế persistence nào được xác minh từ contract model.
