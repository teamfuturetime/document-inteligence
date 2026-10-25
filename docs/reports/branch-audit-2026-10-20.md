# Khảo sát các nhánh dự án ngày 20 tháng 10 năm 2026

Khảo sát chỉ đọc mã nguồn và Git metadata, phục vụ phân công nhóm. Đã dùng `git ls-remote --heads origin`, `git fetch origin --no-tags`, `git ls-tree`, `git log`, `git show` và `git diff`; không checkout, chạy code nhánh khác, push, merge, xóa hoặc đổi tên nhánh. Git CLI truy cập được remote private; GitHub connector trả 404 nên không xác minh settings, PR/issue hoặc Actions hiện tại qua connector. File chưa được theo dõi sẵn trong checkout được giữ nguyên.

## Snapshot remote

Remote: `https://github.com/teamfuturetime/document-inteligence.git`. Snapshot tại thời điểm đọc ngày 20/10/2026, không phải trạng thái bất biến sau ngày này. Số commit là số ahead so với main; số file là tracked files, không phải thước đo chất lượng hay đóng góp cá nhân.

| Nhánh | Head SHA rút gọn | Ahead main | Số file | Nhận xét từ mã nguồn |
| --- | --- | --- | --- | --- |
| main | 94c5101 | 0 | 1 | Chỉ README ở commit đầu |
| nhatquang | f37bfbd | 1 | 146 | Foundation docintel, contracts/generated, fixtures, evaluator, tests, tài liệu; schema đơn đề nghị 7 trường |
| personal/canhtung-main | 61a31ab | 35 | 227 | Workspace backend/pipeline/schemas/evaluation; Tesseract, extraction hóa đơn 5 trường, frontend review, tests/evidence; chưa persistence |
| congtri | 99471ef | 41 | 89 | backend/app và ai_service, upload/storage/SQLAlchemy/Alembic, OCR adapter/rules; kiến trúc khác hai nhánh trên |
| minhthao | da108de | 30 | 67 | backend/app và ai_service, upload/database/preprocessing/OCR/extraction/classification; nhiều phần trùng Trí |
| feat/backend-skeleton | a281029 | 9 | 83 | Nhánh phát triển backend trong dòng công việc của Tùng; không phải một thành viên độc lập |
| chore/ci-checks | 55ae3c6 | 16 | 119 | Nhánh CI trong dòng công việc của Tùng; không phải một vai trò thứ sáu |

Không có nhánh tên Tuấn trong 7 refs này. Không suy từ đó Tuấn chưa làm việc; cần Tuấn xác nhận branch/commit hoặc công việc chưa đẩy lên remote.

## Những khác biệt ảnh hưởng kế hoạch

1. **Không còn đúng rằng mọi nhánh chỉ khởi tạo.** Có implementation OCR, backend và UI ở một số nhánh. Chưa đủ căn cứ gọi các implementation đó hoàn thành yêu cầu chung.
2. **Ba tổ chức mã khác nhau:** docintel ở nhatquang; Python workspace ở personal/canhtung-main; backend/app + ai_service ở congtri/minhthao. Merge cả cây của tất cả nhánh sẽ tạo nhiều application entry points, schemas, dependency/config/CI và evaluator cạnh tranh.
3. **Scope chưa đồng nhất:** foundation minh họa đơn đề nghị 7 trường; Tùng triển khai hóa đơn 5 trường; các nhánh khác có field definitions/classification rộng hơn. Phải chốt schema sản phẩm trước khi chia code.
4. **Cần giữ công sức có giá trị:** ưu tiên kiểm tra Tesseract/model hash/timeout/geometry và UI của Tùng; repository/upload/migration của Trí; xử lý ảnh/aliases của Thao; hợp đồng draft/final/revision/provenance, evaluator và governance từ Quang. Chỉ port phần đạt contract và test chung.

## Các điểm cần review trước khi tiếp nhận

| Nguồn đã đọc | Phát hiện có thể kiểm tra lại | Hành động khi tích hợp |
| --- | --- | --- |
| personal/canhtung-main: backend/src/document_backend/api/extract.py và api/validate.py | Extract theo request và validate payload; chưa thấy workflow persisted revision/confirm/export trong hai API này; README nêu không database | Trí bổ sung storage, immutable run, revision, backend confirmation/export; không coi JSON tải từ UI là bằng chứng đã có workflow cuối |
| personal/canhtung-main: pipeline/src/document_pipeline/ocr.py | Có gọi Tesseract thật, kiểm model/hash, timeout và TSV geometry; page wire đang 1-based | Quang kiểm tra engine/runtime/license và chuyển đổi tọa độ/page theo contract chung bằng tests |
| personal/canhtung-main: evaluation/src/document_evaluation/metrics.py | PRF không tính null-null thành TP; exact_match vẫn cộng null-null trong correct/total | Tuấn giữ metric legacy với tên rõ, bổ sung present/readable accuracy, absent extra-fill, unreadable và document support theo protocol gốc |
| personal/canhtung-main: docs/completion.md và README | Có công bố test counts và benchmark local trên 30 hóa đơn, split 18/12, cùng các hạn chế | Đây là báo cáo của nhánh, **chưa được chạy lại trong lượt khảo sát này**; không dùng làm quality gate chung hoặc xác nhận current CI |
| congtri: ai_service/extraction/rules.py | Confidence được gán 0.8 khi match, 0.0 khi missing | Không coi là calibrated probability; thay bằng method/signals/reasons hoặc unknown theo confidence policy |
| congtri: ai_service/evaluation/extraction_metrics.py | Value bị str()/casefold(), denominators ép tối thiểu 1 | Không dùng làm metric chính của nhóm; không làm mất kiểu/null và phải có zero-denominator policy |
| congtri: backend/app/services/processing.py | Chọn Paddle hoặc EmptyOcrEngine theo config | Empty engine chỉ được dùng trong mode test/mock explicit; default real không thành công giả khi thiếu engine |
| minhthao: ai_service/extraction/engine.py | FieldPattern có confidence mặc định 90.0 | Cần quy đổi thang điểm/chính sách, ghi heuristic; không dùng số mặc định làm chứng cứ chất lượng |
| minhthao: ai_service/extraction/confidence.py | Kiểm ngày qua khoảng day<=31/month<=12 chưa chứng minh ngày tồn tại | Dùng calendar parser và tests 31/02, năm nhuận; không merge rule này nguyên trạng |
| nhatquang: docs/requirements, domain models, evaluator | Tách draft/final, prediction/review, provenance; fixtures không model benchmark | Bảo toàn semantics khi chuyển sang package chung; tránh giữ hai nguồn chuẩn độc lập |

Đây là review định hướng, không phải danh sách đầy đủ lỗi bảo mật hay đánh giá năng lực từng người. Một đoạn code cần sửa không phủ nhận các phần hữu ích khác của nhánh.

## Khuyến nghị nền chung

Ưu tiên **personal/canhtung-main làm ứng viên nền tích hợp**, vì có luồng OCR hóa đơn và UI có thể kế thừa, sau khi nhóm chạy lại install/contracts/tests/native OCR trên đúng SHA và đối chiếu nguồn model. Đây là lựa chọn đề xuất có điều kiện, không kết luận nhánh đã đạt MVP. Nếu điều kiện không đạt trong 48 giờ, chọn nhatquang làm nền hợp đồng và port từng module đạt kiểm tra; không tái viết toàn bộ hoặc merge mù các skeleton.

Tùng điều phối một PR gom nền có manifest nguồn: path đích, path/branch/SHA nguồn, cách chuyển contract, kiểm tra và reviewer. Chỉ sau PR nền vào main mới bắt đầu quy trình 5 nhánh cá nhân liên tục. Không làm thao tác Git destructive để ép nhánh cũ có cùng cây.

Xem [bản phân công và kế hoạch 10 tuần](../planning/team-delivery-plan-2026-10-20.md).
