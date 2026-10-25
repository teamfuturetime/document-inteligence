# Phân công nhóm và kế hoạch hoàn thiện Document Intelligence

**Đề tài AI-02. Nhóm gồm Tùng, Quang, Trí, Thao và Tuấn. Thời gian 20/10/2026 đến 28/12/2026.**

Mục tiêu là một ứng dụng dùng OCR thật để trích xuất dữ liệu từ biểu mẫu tiếng Việt, cho phép đối chiếu, sửa, lưu nháp, xác nhận và xuất JSON đúng bản đã lưu. Nhóm phát triển trên một nền chung, mỗi người chịu trách nhiệm sâu một phần và tích hợp đều qua PR. Tùng là nhóm trưởng; Quang có sở trường AI theo thông tin đã cung cấp. Phân vai chuyên môn cho Trí, Thao và Tuấn dưới đây là đề xuất để nhận việc, có thể đổi người trong buổi khởi động nhưng phải giữ đủ năm trách nhiệm.

**Mốc giao sản phẩm chính là 21/12/2026, hết tuần 9. Tuần 10 đến 28/12/2026 dành cho sửa lỗi và bàn giao dự phòng.** Đây là lịch suy ra từ yêu cầu 9-10 tuần, không phải deadline do giảng viên đã ban hành. MVP bắt buộc phải chạy xuyên suốt trước 30/11, hết tuần 6; không dồn việc merge hoặc dựng evidence đến tuần cuối.

## 1 Kết luận và cách bắt đầu

Vấn đề hiện tại là chưa có nền và hợp đồng chung được tích hợp vào main, trong khi các nhánh đã phát triển khác nhau. Khảo sát remote ngày 20/10 cho thấy main chỉ có README; Quang có foundation; Tùng đã có code OCR và UI hóa đơn; Trí và Thao có các phần backend/OCR khác. Số commit hoặc số file không chứng minh hoàn thành MVP. Xem [khảo sát nhánh](../reports/branch-audit-2026-10-20.md) để biết SHA và phần nào mới đọc code, chưa chạy lại.

Nhóm cần làm ngay ba việc: chọn một nền tích hợp, chốt scope/schema và xác nhận người chịu trách nhiệm từng module. Đề xuất kiểm tra nền của Tùng trước vì có thể tận dụng luồng OCR thật; giữ các contracts, kiểm thử và nguyên tắc evidence tốt từ foundation Quang. Trí và Thao chuyển các phần hữu ích vào module đích thay vì tiếp tục xây ứng dụng riêng.

Không thể bảo đảm năm người hoàn toàn không có phụ thuộc. Cách hạn chế ảnh hưởng là có owner chính từng module, contract được chốt sớm, tests ở ranh giới và PR nhỏ. Mỗi người có nhánh làm việc riêng liên tục, nhưng phần hoàn thành phải vào main trong tuần; không đợi hết 10 tuần mới merge.

## 2 Phân vai và nhánh làm việc

| Thành viên | Vai trò chịu trách nhiệm chính | Nhánh đề xuất dùng liên tục | Đầu ra chính |
| --- | --- | --- | --- |
| Tùng | Nhóm trưởng, kiến trúc, contracts, tích hợp và phát hành | personal/canhtung-main | Nền chung, schemas/API thống nhất, CI/Docker, bản tích hợp và hồ sơ bàn giao |
| Quang | AI, tiền xử lý, OCR, extraction, confidence | nhatquang | Pipeline thật, evidence theo trường, abstention, cấu hình/model có truy vết, phân tích lỗi AI |
| Trí | Backend nghiệp vụ, upload, lưu trữ, revision và export | congtri | API/services và SQLite/migrations, lưu prediction/review riêng, xác nhận và export đúng revision |
| Thao | Frontend, đối chiếu ảnh, trải nghiệm review | minhthao | Upload/trạng thái, ảnh và evidence, sửa/lưu/confirm/export, xử lý lỗi và responsive |
| Tuấn | Dữ liệu, evaluator, kiểm thử hệ thống và evidence | tuan, nhánh mới đề xuất | Dataset/gold/split, metrics/taxonomy, E2E, báo cáo chất lượng và regression |

Nhánh của Quang được xác nhận từ phiên làm việc; các ánh xạ tên Tùng/Trí/Thao phù hợp refs và author đã đọc, cần chính chủ xác nhận tại buổi nhận việc. Không thấy nhánh Tuấn trong 7 refs hiện tại; Tuấn xác nhận có branch khác hay tạo nhánh đề xuất từ main sau gom nền. Không coi feat/backend-skeleton hoặc chore/ci-checks là thành viên thứ sáu; đó là công việc trong dòng nhánh của Tùng.

Tùng không chỉ quản lý: Tùng trực tiếp làm contracts, tích hợp module, hạ tầng chạy và phát hành. Tuấn không chỉ viết báo cáo: Tuấn trực tiếp phát triển evaluator, generator/manifest checks và E2E. Mỗi tác giả tự viết tests module mình; Tuấn phụ trách kiểm thử độc lập ở cấp hệ thống, không nhận toàn bộ trách nhiệm test thay bốn người còn lại.

## 3 Phạm vi sản phẩm và mức ưu tiên

### 3.1 Yêu cầu gốc phải bảo toàn

COURSE_REQUIRED gồm MVP-01 OCR, MVP-02 schema extraction, MVP-03 confidence, MVP-04 review/sửa, MVP-05 validation, MVP-06 export JSON và DATA-01 synthetic/sample only. Bốn evidence bắt buộc là EVD-01 golden dataset, EVD-02 field-level metrics, EVD-03 error taxonomy, EVD-04 model/config versioning. ENG-01..04 là yêu cầu nền về cài lại, cộng tác, checks và sự trung thực về khả năng.

Giảng viên chưa bắt buộc làm đồng thời hóa đơn và đơn từ, chưa có target accuracy hoặc số ảnh tối thiểu được biết. Schema đơn đề nghị bảy trường trong foundation là PROVISIONAL. Đề xuất dưới đây tận dụng code hiện có, cần Tùng ghi ADR và cả nhóm chốt ở tuần 1; không âm thầm thay yêu cầu gốc.

### 3.2 P0 bắt buộc hoàn thành trước khi mở rộng

| Nhóm chức năng | Phạm vi cam kết | Định nghĩa hoàn thành |
| --- | --- | --- |
| Loại tài liệu chính | Đề xuất hóa đơn tiếng Việt đánh máy một trang, phần header/tổng tiền | Có schema và field definitions chốt; không hứa hỗ trợ mọi hóa đơn hoặc line items |
| Đầu vào | PNG/JPG; chọn schema rõ; PDF một trang được giữ nếu code kế thừa vượt kiểm tra | Kiểm bytes thật/size/pixel/page; lỗi có mã; không tin extension |
| OCR và extraction | Một engine baseline thật, alias/nhãn/vị trí/ghép dòng, có bằng chứng và null khi không chắc | Không đọc gold, không trả mock thành real, thiếu engine báo unavailable |
| Confidence và validation | Theo từng field, method/version/reasons; strict types, calendar và liên trường | Heuristic ghi heuristic, unknown được phép; validation không tự sửa dữ liệu nguồn |
| Review | Ảnh cạnh form, highlight nếu có evidence, sửa/xóa/lưu nháp/reload/xử lý conflict | Giá trị máy bất biến, reviewed-null giữ xóa, không mất sửa âm thầm |
| Persistence | SQLite local, migrations, lưu document/run/prediction/revision/events | Restart còn dữ liệu; run mới không ghi đè review cũ |
| Confirm và export | Backend đọc revision persisted, mới nhất, confirmed và valid | Trả JSON có document/run/revision/schema/provenance; từ chối stale/invalid/unconfirmed |
| Evidence | Golden có quyền, split/grouping, field metrics trước review, taxonomy, run metadata | Lệnh tái lập và report trên model thật; fixture chỉ kiểm tra contract |
| Chạy và bàn giao | Native trên môi trường chốt, Docker local, CI và E2E thực | Có kết quả đúng commit/lock; hạn chế và phần chưa chạy ghi rõ |

Giới hạn khởi đầu đề xuất: một trang, 5 MiB, 16 triệu pixel và deadline xử lý 30 giây; đây là config PROVISIONAL cần thống nhất với code nền Tùng đang dùng 10 MiB/25M pixel. Chỉ có một cấu hình runtime được áp dụng và kiểm tra ở UI/API/worker; không giữ hai bộ limit khác nhau. Demo local/single-user; không tự deploy cloud hoặc mở ứng dụng chưa authentication ra Internet.

### 3.3 Các trường dữ liệu

Hóa đơn chính gồm invoice_number, invoice_date, seller_name, total_amount, currency. invoice_number là string giữ số 0; invoice_date ISO date có ngày tồn tại; total_amount là integer VND trong miền an toàn đã chốt cho JSON/JavaScript, không floating point; currency là enum theo scope, ban đầu VND. Nếu mở đa tiền tệ, cần ADR và decimal-string/rounding rõ. Năm field bắt buộc khi xuất cuối theo schema đề xuất; draft vẫn cho thiếu/sai kèm issues. Không suy tiền tệ từ giả định khi ảnh không có bằng chứng.

Đơn đề nghị mở rộng giữ bảy field foundation: full_name, student_id, date_of_birth, class_name, faculty, request_content, request_date. student_id luôn string, ngày sinh không sau ngày đơn. Schema này được thiết kế trong tuần 1 để frontend/backend không hard-code chỉ một loại tài liệu; extraction thật và dataset tương ứng triển khai sau P0, qua cổng quyết định tuần 6.

### 3.4 P1 mục tiêu nâng cao sau cổng MVP

Ưu tiên theo thứ tự: lịch sử run/review và so sánh kết quả trước/sau; trang evidence chất lượng có filter theo field/error/config; thêm đơn đề nghị bảy trường; PDF một trang nếu chưa giữ ở P0; batch nhỏ có giới hạn nếu còn năng lực. Nhóm chọn tối đa ba hạng mục P1 tại cuối tuần 6, trong đó lịch sử/audit cần thiết cho correctness không được cắt khỏi P0; P1 chỉ là phần xem/so sánh thuận tiện hơn. Mọi P1 phải có data/tests và không làm hỏng P0.

Các điểm thuyết phục khi demo là OCR thật, đối chiếu vùng nguồn, giữ lại được sửa sau reload, từ chối export bản cũ, xem nguyên nhân confidence, so sánh cấu hình bằng evidence thật và xử lý được trường thiếu/không đọc được. Những điểm này có giá trị hơn số lượng framework hoặc nhãn AI.

### 3.5 P2 thí nghiệm và phạm vi chưa nhận

Chỉ nhận tối đa một thí nghiệm có timebox: so sánh VLM/LLM với baseline trên cùng protocol nếu đã có tài nguyên/quyền và giả thuyết từ lỗi; hoặc một nghiên cứu review/nhập tay nhỏ có phương pháp. Không dùng API trả phí, tải model lớn, mời người hoặc gửi data ra ngoài chỉ vì ghi trong kế hoạch. Người có thẩm quyền quyết định khi cần. Không hứa chữ viết tay, nhiều trang, line items, fine-tuning, SaaS nhiều tổ chức, realtime hoặc mọi loại tài liệu trong 10 tuần.

## 4 Chọn nền và xử lý phần đã làm trùng

### 4.1 Quyết định trong 48 giờ đầu

Tùng và Tuấn chạy lại ứng viên personal/canhtung-main tại SHA khảo sát trên môi trường nhóm: frozen install, generated schemas/types, tests, một OCR thật trên synthetic sample và review hiện có. Quang kiểm nguồn/checksum model và output spans. Trí xem ranh giới storage/revision còn thiếu. Thao xác minh UI gọi backend nào và export hiện đang ở client hay server. Không tải engine/model ngoài phạm vi được nhóm chọn chỉ để minh họa báo cáo.

Nếu các checks nền đạt, dùng tổ chức package của Tùng làm cấu trúc chung: backend, pipeline, schemas, evaluation, frontend, data, docs. Nếu ứng viên không đủ chạy sau hai ngày có timebox, dùng nền nhatquang làm phương án dự phòng và port module Tùng đạt tests; cả nhóm chỉ có một stack đích. Không duy trì đồng thời docintel, document_backend và ai_service như ba ứng dụng production độc lập.

### 4.2 Những phần ưu tiên kế thừa

| Nguồn | Phần cần xem để dùng lại | Điều kiện tiếp nhận |
| --- | --- | --- |
| Tùng | Tesseract adapter/model lock, preprocessing/geometry, extractor hóa đơn, React review, tests/CI | Chạy lại đúng SHA; giữ nguyên lịch sử nguồn; bổ sung persistence/export authority và contract còn thiếu |
| Quang | Draft/final, raw/normalized/review separation, reviewed-null, provenance, manifest và metrics đầy đủ, docs/traceability | Port vào nguồn chuẩn duy nhất; fixtures vẫn ghi fixture; không bê cả application thứ hai |
| Trí | Upload/storage/repository/migration, orchestration và kiểm file | Đổi về API/schema/config chung; kiểm transaction, paths, provider-empty và tests |
| Thao | Tiền xử lý/aliases/layout và các tests phù hợp; frontend nào dùng được sau audit | Không giữ confidence mặc định như xác suất; calendar validation đúng; không viết trùng pipeline Quang |
| Tuấn | Kiểm tra chéo cả bốn nguồn và tạo integration test cho phần port | Không trộn ba evaluator có công thức khác nhau thành cùng một metric |

Mỗi phần port có bản ghi source branch/SHA/path, path đích, khác biệt contract, tests và reviewer. Một PR gom nền có thể lớn vì kế thừa scaffold; phải chia review theo module, ghi rõ ngoại lệ một lần. Từ sau PR nền, mỗi PR chỉ một mục tiêu. Không import toàn bộ module trùng chỉ để ghi nhận đóng góp; ghi công qua source lineage, issue/PR và review thực chất.

### 4.3 Đưa năm nhánh về cùng nền một cách an toàn

Đây là thao tác nhóm cần làm sau khi duyệt kế hoạch, chưa được thực hiện trong lượt phân công. Trước hết mỗi người kiểm tra git status, commit/push các thay đổi có giá trị và tạo mốc lưu nhánh cũ nếu cần. Không reset/force-push. Tùng đưa PR nền đã kiểm tra vào main. Với nhánh cá nhân khác kiến trúc, chính chủ và Tùng merge main vào nhánh, giải conflict theo cây nền đã chọn rồi chuyển từng phần cũ cần giữ; reviewer xem diff tổng. Nhánh cũ và commits vẫn còn để truy vết, không xóa trong lúc chuyển.

Nếu giải conflict quá rối, cả nhóm có thể chọn năm nhánh cá nhân mới xuất phát từ main đã chốt và giữ nguyên các nhánh cũ để tham khảo. Đây là lựa chọn sạch hơn trong trường hợp cần thiết, không tự đổi tên nhánh của ai. Sau tuần 1 mỗi người chỉ có một nhánh cá nhân đang phát triển chính; các task branches cũ đóng/đánh dấu hoàn tất khi chủ sở hữu đồng ý.

## 5 Ranh giới mã nguồn và quyền sửa file

Cây dưới đây là cấu trúc đích đề xuất theo ứng viên Tùng, không khẳng định đang tồn tại trên nhatquang. Nếu chọn phương án dự phòng, Tùng phải ghi một bảng ánh xạ path tương đương trước khi mọi người bắt đầu sửa.

| Module hoặc file | Owner chính | Người review | Quy tắc phối hợp |
| --- | --- | --- | --- |
| schemas/src/document_contracts, schema generators và contracts examples | Tùng | Quang và Trí; Thao/Tuấn review phần mình dùng | Nguồn chuẩn chung; đổi semantics phải có ADR/version và cập nhật consumers |
| pipeline/src/document_pipeline/preprocessing, ocr, extraction, inference/config engine | Quang | Tuấn; Trí review interface | Nhận input hợp lệ, trả typed result/errors; không ghi DB hoặc đọc gold |
| backend/src/document_backend/api routes và services nghiệp vụ, storage, jobs, migrations | Trí | Tùng; Tuấn review tests | Trí sở hữu business API; app wiring/config khởi tạo phối hợp Tùng |
| backend main/app assembly, common Settings, root dependency files, CI/Compose/Docker | Tùng | Trí hoặc Tuấn | Người khác yêu cầu thay đổi qua PR nhỏ; không cùng sửa lockfile tự do |
| frontend/src/features, components, styles, API client và UI tests | Thao | Trí và Tuấn | Consume generated types; không tự đổi backend schema hoặc tự tạo final JSON |
| evaluation/src/document_evaluation, data/generators/manifests, system/E2E tests | Tuấn | Quang; Tùng review workflow | Gold chỉ trong data/evaluation; model code không import labels |
| scripts/module checks và configs theo module | Owner module | Tuấn | Mỗi script có nơi dùng; không nhân đôi công thức evaluator |
| docs kiến trúc/quyết định/phát hành | Tùng | Owner module tương ứng | Mỗi người viết docs phần mình; Tùng giữ nguồn điều hướng và quyết định chung |

Tests nằm cạnh module thuộc tác giả module; Tuấn quản lý ca tích hợp và E2E. Generated schemas/types không ai chỉnh tay. Trong PR thay contracts, Tùng sinh backend contracts và cập nhật tất cả generated outputs; Thao phối hợp generator frontend. Lockfiles được sinh bằng công cụ từ manifest đã review, không sửa conflict thủ công hoặc giữ hai bản khóa cho cùng app. Với files chung, báo trong issue/PR trước khi sửa; owner chỉ là điểm phối hợp, không độc quyền kiến thức hay cấm người khác sửa lỗi khẩn cấp có review.

### 5.1 Quy tắc tránh chồng việc khi triển khai song song

Mỗi task ghi danh sách path được sửa trước khi bắt đầu. Quang sửa pipeline và tests của pipeline; Trí sửa backend nghiệp vụ và tests backend; Thao sửa frontend và tests UI; Tuấn sửa data/evaluation và tests hệ thống; Tùng sửa contracts, assembly và hạ tầng chung. Tuấn phát hiện lỗi AI/API/UI thì mở lỗi có repro để owner sửa, không đồng thời viết lại logic của owner. Tùng tích hợp qua interface, không tự chép lại module đang được người khác triển khai.

Một file nguồn chỉ có một người đang sửa trong cùng thời điểm. Nếu task cần ra ngoài vùng sở hữu, tác giả ghi file/lý do và trao đổi owner trước; owner chọn tự làm PR đầu vào hoặc bàn giao rõ quyền sửa trong task. Các file dùng chung như Settings, app entry point, dependency manifests/lockfiles, contract models, generators và CI do Tùng điều phối từng lượt; PR khác có thể tiếp tục ở module riêng trong lúc chờ. Đổi quyền sở hữu phải cập nhật bảng phân công và báo cho consumer trước khi sửa.

Không đổi tên trường, kiểu dữ liệu, ý nghĩa null, error codes, coordinate frame hoặc export policy chỉ trong module của mình. Thay đổi hành vi ở ranh giới cần producer và consumer cùng review dù không trùng file. Một lần chỉnh source schema sinh nhiều generated files vẫn là một thay đổi có Tùng chịu trách nhiệm, không chia cho nhiều người chỉnh tay từng bản sao. Domain models Pydantic được backend sử dụng vẫn là nguồn chuẩn; nếu đóng thành package document_contracts thì đó là nơi duy nhất định nghĩa models, không duy trì thêm bộ domain schema cạnh tranh trong backend.

### 5.2 Cách làm khi đầu vào chưa sẵn sàng

Consumer triển khai theo contract/examples đã chốt và dùng adapter hoặc fixture có nhãn để viết unit/component tests, thay vì chờ toàn bộ module upstream. Trong cùng task, tách phần không phụ thuộc thành PR nhỏ: UI states/form trước kết nối API; backend persistence trước OCR thật; evaluator trước predictions model; pipeline adapter trước business workflow. Chưa có engine/API thật thì trạng thái tích hợp vẫn pending, không ghi đã đạt E2E hoặc model benchmark.

Nếu đầu vào chậm quá một buổi làm việc, consumer ghi artifact đang thiếu và việc bị chặn; Tùng cùng producer chốt cách bàn giao tối thiểu trong ngày làm việc kế tiếp. Consumer chuyển sang tests/docs/lát cắt độc lập đã có trong task; không tự xây API, evaluator hoặc pipeline thứ hai để né phụ thuộc. Nếu phải hỗ trợ sửa module khác, chỉ một người nhận file đó và ghi rõ bàn giao với owner. Thời gian review/tích hợp dùng ngân sách phối hợp ở mục 14, không tính như task mới phát sinh vô hạn.

## 6 Hợp đồng phối hợp cần đóng băng sớm

### 6.1 Đầu vào đầu ra giữa các phần

| Ranh giới | Đầu vào | Đầu ra và người chịu trách nhiệm |
| --- | --- | --- |
| Thao sang Trí | Upload multipart, document_type/schema version, idempotency key khi cần | Document ID + metadata/status hoặc error envelope; Trí |
| Trí sang Quang | Document/page hợp lệ, bytes/path do storage cấp, schema và resolved inference config; không annotation path | OCR spans + FieldPrediction + provenance/version/errors; Quang |
| Quang sang Trí | Machine prediction bất biến, raw/normalized/evidence, confidence method/reasons | Trí lưu ExtractionRun và prediction snapshot, không nhận reviewed values từ AI |
| Trí sang Thao | URL ảnh qua API, run/status, field definitions, predictions/revision/issues | Thao hiển thị nguồn, sửa draft và dùng expected_revision |
| Thao sang Trí khi lưu | Reviewed fields, explicit is_reviewed/null, run_id và expected_revision | Revision mới/event hoặc 409, draft invalid vẫn lưu kèm issues |
| Trí sang client khi export | Revision persisted mới nhất, confirmed, valid | ExportArtifact có provenance và revision; không tin approved flag hoặc dữ liệu final client gửi |
| Quang sang Tuấn | Predictions máy trước review + engine/config/runtime metadata | Tuấn chấm với gold ngoài inference, report/counts/taxonomy/run manifest |

Không cần microservices cho từng người. Pipeline là package sau interface, worker local có giới hạn; backend giữ lifecycle/storage. Chỉ tách process/service OCR nếu dependency/runtime buộc phải tách và có ADR, timeout/error contract cùng test tích hợp. Không mặc định PostgreSQL/MinIO/Redis/Kubernetes chỉ để chia việc.

### 6.2 Các quy ước bắt buộc trong hợp đồng tuần 1

Tách Document, ExtractionRun, OCRSpan/Token, FieldPrediction, ReviewRevision, ReviewEvent, ValidationIssue và ExportArtifact. Raw, normalized và reviewed là ba giá trị khác nhau. Trường chưa review khác trường đã review thành null. Khi người dùng xóa, không dùng reviewed_value or machine_value để khôi phục máy.

Chốt page index và coordinate frame trong wire contract. Đề xuất page_index 0-based, pixels ảnh gốc, gốc top-left, có width/height và transform mapping; UI hiển thị trang 1. Code Tùng hiện dùng page=1 cần adapter có tests khi port. Thiếu evidence dùng unavailable/unknown, không bịa bbox. Nếu đổi contract hiện có phải tăng version/migration tương ứng, không tái dùng version cũ với nghĩa khác.

Chốt statuses document/run/review và HTTP errors. Tối thiểu có 413/415/422 đầu vào, 503 provider unavailable, failed/timeout rõ, 409 revision conflict/export stale/not confirmed. Mỗi lỗi có code/message/request ID an toàn, không stack trace hoặc đường dẫn nội bộ. Retry bị chặn/giới hạn theo từng operation, không sinh các run trùng do double-click mà không có policy.

Chốt policy Unicode NFC/whitespace/date/money/ID và gold present/absent/unreadable. Giữ giá trị nhìn thấy dù sai nghiệp vụ; không đổi nhãn ngày 31/02 thành ngày đúng hoặc giả absent để metric đẹp. Nếu model abstain vì invalid source, báo lý do riêng; validation và extraction accuracy là hai phép kiểm tra khác nhau.

Tùng bàn giao field definitions và examples sơ bộ trong tuần 1, đóng băng contract chạy được trong tuần 2; Trí, Quang, Thao và Tuấn có thể triển khai song song bằng contract fixtures có nhãn. Khi chuyển sang engine thật, fixture mode vẫn explicit và metrics fixture không được trộn model benchmark.

### 6.3 Thay đổi hợp đồng sau khi đã chốt

Người cần thay đổi mở đề xuất kèm requirement, ví dụ payload trước/sau, migration và consumer bị ảnh hưởng. Tùng và owner consumers review trong một ngày làm việc nếu không có lịch khác; thay đổi breaking tạo version mới, không âm thầm ghi đè. PR producer và consumers tích hợp cùng đợt, main phải build/typecheck/test được. Trường bổ sung compatible được tài liệu hóa; không tự đổi tên field/backend path trong PR UI hoặc evaluator.

### 6.4 Lịch bàn giao đầu vào để không chờ nhau đến cuối task

Các mốc dưới đây là phần bàn giao nhỏ nằm trong 45 task, không phải thêm 45 đầu việc mới. Hợp đồng sơ bộ mở đường cho phát triển; chỉ artifact đã qua checks và merge mới được ghi là đầu vào tích hợp chính thức.

| Hạn bàn giao | Producer và artifact | Consumer nhận việc ngay |
| --- | --- | --- |
| Tuần 1, sau TG-01 | Tùng bàn giao field definitions, interface skeleton, ownership và ví dụ sơ bộ; TG-02 đưa nền đã kiểm vào main | Quang làm adapter, Trí thiết kế DB, Thao làm states/form, Tuấn làm generator/protocol trên cùng nền |
| Đầu tuần 2, trong TG-03 | Tùng chốt typed contracts và examples success/error/review-null; sinh schemas/types vào main | Cả bốn người khóa theo cùng version; hoàn thiện tests interface trước khi producer chạy thật |
| Tuần 2 đến đầu tuần 3 | Trí bàn giao upload/storage đầu tiên từ TR-02; Quang bàn giao OCRSpan/typed errors đầu tiên từ Q-02 | Thao nối upload/status; Trí nối pipeline; Tuấn thêm upload/provider/geometry tests |
| Trong tuần 3 | Quang bàn giao prediction tối thiểu từ Q-03; Trí bàn giao lưu/đọc run tối thiểu từ TR-03/04 | Thao nối source/result; Tuấn chạy lát cắt OCR thật. Q-03 tiếp tục cải thiện extraction đến tuần 4 |
| Tuần 4 đến đầu tuần 5 | Trí bàn giao save draft/revision từ TR-05 và error examples | Thao nối lưu/xóa/reload/conflict; Tuấn kiểm null, hai tab và restart ngay |
| Tuần 5 đến hết tuần 6 | Trí bàn giao confirm/export từ TR-06 và phần reprocess an toàn P0 của TR-07 | Thao nối tải JSON server; Tuấn hoàn thiện E2E; Tùng kiểm G3 từ main |
| Sau G3, tuần 7-8 | Tùng chốt P1; Tuấn bàn giao report schema/artifacts; Trí/Quang bàn giao APIs/outputs nâng cao đã chọn | Thao xây UI theo artifact/version đã có; không làm màn hình cho P1 chưa được nhận |
| Cuối tuần 8 đến tuần 9 | Tùng chốt candidate commit; Quang bàn giao config khóa Q-09; Tuấn chạy TN-09 | Cả nhóm chỉ sửa lỗi có kiểm lại; hồ sơ và demo dùng đúng candidate/run được nghiệm thu |

Phiếu bàn giao trong issue/PR phải có producer/consumer, task ID, contract version, paths/artifact, PR và merge commit SHA, lệnh/checks kèm kết quả, giới hạn còn lại và thời điểm consumer xác nhận nhận được. Consumer kiểm ví dụ bằng parser/typecheck/test của mình trong một buổi kế tiếp. Chỉ dẫn tới file trên máy cá nhân hoặc nhắn “đã xong” chưa phải bàn giao. Trễ mốc thì cập nhật dependency và lịch chung ngay, không âm thầm chuyển rủi ro sang người nhận.

## 7 Quy trình Git cho năm nhánh cá nhân liên tục

### 7.1 Chu kỳ hằng ngày và hằng tuần

Mỗi người làm trên nhánh được phân công, mỗi lần chỉ một task chính đang active và tối đa một task nhỏ chờ review. Đầu buổi fetch và merge main nếu có cập nhật; cuối buổi commit phần có ý nghĩa, push nhánh cá nhân và cập nhật issue: đã xong, evidence, đang vướng ai, việc tiếp theo. Không push trực tiếp main.

Một PR là một hành vi hoặc một lát cắt có thể review và kiểm tra. Mở draft sớm khi contract/interface cần phản hồi. Tối thiểu mỗi tuần mỗi người tích hợp một phần hoàn thành; đây là nhịp phối hợp, không ép tạo commit/PR hình thức. Nếu một task kéo dài nhiều ngày, chia theo seam có feature flag/contract thay vì làm tất cả trong một PR khổng lồ.

Tùng xếp thứ tự merge theo dependencies, reviewer khác tác giả xác nhận, CI đúng head SHA đạt rồi merge. Sau mỗi merge, các nhánh consumer cập nhật main và chạy checks liên quan. Cuối tuần demo trên main chung với backend và pipeline thật; fixture chỉ dùng kiểm trạng thái chưa có và phải ghi rõ.

### 7.2 Cách merge phù hợp với yêu cầu giữ nhánh lâu dài

Đề xuất dùng **Create a merge commit** cho các PR từ năm nhánh cá nhân và `git merge origin/main` để đồng bộ lại nhánh. Không rebase/force-push nhánh đã chia sẻ. Sau merge, tiếp tục nhánh đó cho task kế tiếp, không xóa nhánh. Quy tắc này giữ quan hệ ancestor để PR sau không lặp lại commits đã được squash ở main.

Nếu nhóm chọn squash để lịch sử ngắn, nên đổi sang task branches xuất phát mới từ main; không trộn squash với việc giữ nguyên nhánh cá nhân liên tục mà không có chiến lược đồng bộ. Với lựa chọn merge commits, không bật yêu cầu linear history mâu thuẫn trên main. Đây là điều chỉnh theo nhu cầu nhóm so với GitHub Flow dùng branch ngắn; không tuyên bố branch cá nhân dài hạn luôn tốt hơn.

Ví dụ thao tác của Quang sau khi đã có nền chung; các thành viên thay đúng tên branch của mình. Chỉ thực hiện khi working tree sạch hoặc thay đổi đã được lưu an toàn:

```bash
git status
git fetch origin
git switch nhatquang
git merge origin/main
git diff --check
# Chạy checks phù hợp của nền chung
git push origin nhatquang
```

Khi conflict, người làm dừng ở file conflict, trao đổi owner và giải theo contract đã chốt, chạy lại tests trước commit. `git merge --abort` chỉ để bỏ một merge đang diễn ra sau khi đã bảo vệ công việc; không thay bằng reset --hard. Khi main lỗi, ưu tiên revert PR gây lỗi bằng commit/PR mới hoặc hotfix có reviewer; không sửa lịch sử để che sự cố.

### 7.3 Review và cấu hình GitHub

| Tác giả | Reviewer chính | Reviewer bổ sung khi cần |
| --- | --- | --- |
| Tùng | Trí | Tuấn với CI/evidence; Quang với model/contract AI |
| Quang | Tuấn | Tùng/Trí nếu contract hoặc integration đổi |
| Trí | Tùng | Thao với request/response; Tuấn với export/revision |
| Thao | Trí | Tuấn với E2E/accessibility; Tùng với generated contracts |
| Tuấn | Quang | Tùng với workflow/report; người khác review chéo nhãn |

Reviewer review semantics và evidence, không chỉ format; tác giả không tự duyệt. Tùng có người backup là Trí để không thành nút thắt. Cấu hình do người có quyền thực hiện: PR trước merge, ít nhất một review khác tác giả, checks ổn định của nền chung, cấm force-push/delete main, resolve conversations và quản lý admin bypass theo gói/quyền thực tế. Repo private có thể có giới hạn gói GitHub; nếu chưa enforce tự động được, áp dụng policy thủ công và ghi rõ.

Không lấy tên check backend-checks của Quang và Backend checks của Tùng như cùng một setting. Tùng chọn tên ổn định sau gom workflow, chạy một PR thật rồi mới cấu hình required checks. CODEOWNERS dùng handles có quyền đã xác minh; file example không tự bật mandatory review. Nhánh CI cũ có run trước đây không chứng minh head mới đã xanh.

### 7.4 Hàng đợi merge và kiểm tra sau tích hợp

Tùng hoặc Trí khi được bàn giao điều phối một PR tại một thời điểm theo thứ tự: nền/contracts tương thích → producer → consumer → tests/evidence. Với nhiều PR đã sẵn sàng, ưu tiên PR tạo đầu vào đang chặn người khác và PR sửa lỗi main. Các thành viên tiếp tục code trên nhánh riêng trong lúc chờ review; không ai đẩy trực tiếp lên main để vượt hàng đợi.

Trước merge, nhánh PR cập nhật main, kiểm diff không chứa module cũ hoặc thay đổi ngoài scope, rồi chạy lại checks cho phần bị tác động. Nếu main đổi làm kết quả checks trước đó không còn đủ chứng minh tương thích, chạy lại checks trên tổ hợp mới hoặc merge candidate. Thay đổi breaking phải triển khai bước tương thích trước: thêm version/API mới, chuyển consumers rồi mới bỏ bản cũ khi không còn dùng; không để main lỗi trong lúc chờ PR nối tiếp. Việc chưa có tính năng có thể thể hiện unavailable hoặc feature flag rõ, không trả success giả.

Sau merge, Tuấn hoặc owner kiểm smoke test trên đúng SHA main mới, consumer cập nhật main và kiểm interface liên quan; cuối tuần chạy luồng thật chung. Nếu main bị hỏng, tạm dừng merge tính năng, một owner sửa/revert qua PR và người còn lại tiếp tục phần độc lập. Mục tiêu phản hồi trong một ngày làm việc; nếu không sửa kịp một buổi thì ưu tiên revert PR gây lỗi theo lịch sử, giữ nhánh tác giả để sửa và mở lại. Không giữ main hỏng nhiều ngày rồi cộng dồn thêm PR. Mỗi lần demo ghi commit/checks/run thật, không dùng bản riêng trên máy tác giả thay cho bản tích hợp.

## 8 Lịch mười tuần và cổng nghiệm thu

| Tuần | Khoảng ngày | Sản phẩm chung phải xem được ở cuối tuần |
| --- | --- | --- |
| 1 | 20/10-26/10 | Chọn nền, chốt scope/field definitions và ownership; PR gom nền vào main; cả 5 người chạy cùng commit và có task đầu |
| 2 | 27/10-02/11 | Contract v1/v2 mới nếu cần đã freeze; upload lưu document, OCR baseline và UI gọi API cơ bản; dataset/split protocol sẵn |
| 3 | 03/11-09/11 | Một lát cắt thật upload → OCR → prediction persisted → UI evidence; run/config truy vết; baseline validation lần đầu |
| 4 | 10/11-16/11 | Extraction các field chính, dữ liệu nhiều layout, draft/reload và document status; dashboard evidence nền; không còn làm pipeline riêng |
| 5 | 17/11-23/11 | Sửa/xóa/lưu nháp/revision conflict và review events chạy thật; candidate confirm/export backend; E2E regression chính |
| 6 | 24/11-30/11 | P0 MVP thật xuyên suốt, persisted confirm/export đúng revision, tests failure cases, Docker/cài lại và baseline report; quyết định tối đa 3 P1 |
| 7 | 01/12-07/12 | P1 đã chọn: run history/compare, evidence dashboard, schema đơn đề nghị hoặc PDF; đo confidence trên validation |
| 8 | 08/12-14/12 | Hoàn tất P1 có data/tests, usability/responsive/security/performance fixes; khóa feature và config trước final test |
| 9 | 15/12-21/12 | Chạy test độc lập, báo cáo thật, sửa lỗi blocker, rehearsal và bàn giao sản phẩm chính từ main |
| 10 | 22/12-28/12 | Dự phòng lỗi/chạy lại cần thiết, cài máy sạch, đóng hồ sơ và bảo vệ; không mở hạng mục lớn mới |

**Cổng G1 cuối tuần 1:** một cây nguồn chuẩn, scope/schema/owner rõ, năm máy chạy được hoặc ghi blocker có người xử lý. **G2 cuối tuần 3:** có inference thật và prediction persisted; nếu chưa đạt, dừng thêm model/provider và ưu tiên baseline. **G3 cuối tuần 6:** toàn bộ P0 qua checklist; nếu chưa đạt thì tạm bỏ mọi P1/P2. **G4 cuối tuần 8:** feature freeze, chốt config/test protocol; không tune theo final test. **G5 cuối tuần 9:** release candidate, report/run/dataset/version và demo thống nhất. Không dùng skipped model tests hoặc fixtures để vượt cổng.

### 8.1 Lịch phối hợp của năm người

Mã task ở bảng này được mô tả chi tiết trong mục phân công cá nhân; không phải số GitHub issue. Các task có thể kéo qua nhiều tuần, nhưng phải có phần nhỏ tích hợp giữa chừng. Phụ thuộc được mở khi artifact tương ứng đã được review, không phải luôn chờ cả work package kéo dài hoàn thành; owner ghi rõ output nào đã sẵn sàng trong issue để consumer bắt đầu.

| Tuần | Tùng | Quang | Trí | Thao | Tuấn |
| --- | --- | --- | --- | --- | --- |
| 1 | TG-01, TG-02 | Q-01 | TR-01 | TH-01 | TN-01, mở TN-02 |
| 2 | TG-03 | Q-01, Q-02, mở Q-03 | TR-02, TR-03 | TH-02 | TN-02, TN-03 |
| 3 | TG-04 | Q-02, Q-03 | TR-03, TR-04 | TH-02, TH-03 | TN-03, TN-04, mở TN-05 |
| 4 | TG-05, mở TG-06 | Q-03, Q-04 | TR-04, TR-05 | TH-03, TH-04 | TN-04, TN-05, TN-06 |
| 5 | TG-05, TG-06 | Q-04, Q-05 | TR-05, TR-06 | TH-04, TH-05 | TN-05, TN-06 |
| 6 | TG-06, duyệt G3 | Q-05, duyệt G3 | TR-06, TR-07 phần P0 | TH-05, mở TH-06 | TN-05, TN-06, duyệt G3 |
| 7 | TG-07, mở TG-08 | Q-06 hoặc Q-07 | TR-07, TR-08 nếu nhận | TH-06, TH-07 | TN-07, mở TN-08 |
| 8 | TG-07, TG-08 | Q-06, Q-07; Q-08 nếu được chọn | TR-08 nếu nhận, TR-09 | TH-07, TH-08 | TN-07, TN-08 |
| 9 | TG-08, TG-09 | Q-09 | TR-09 | TH-08, TH-09 | TN-09 |
| 10 | TG-09, buffer | Q-09, fixes | TR-09, fixes | TH-09, fixes | TN-09, recheck |

## 9 Phân công chi tiết của Tùng

**Trách nhiệm:** giữ một sản phẩm chung chạy được; quyết định scope/architecture cùng nhóm; trực tiếp làm contracts, assembly, CI/Docker/release. Không tự ôm toàn bộ code backend hoặc sửa AI thay Quang. Reviewer chính: Trí, có Tuấn hỗ trợ chất lượng. Những giờ dưới đây là ước lượng công việc tập trung, chưa gồm review/buffer.

### TG-01 Chốt phạm vi và tiếp nhận phần đã làm

Tuần 1, khoảng 4 giờ. Requirement MVP-01..06, ENG-02/04; BL-001. Phụ thuộc: khảo sát nhánh và thông tin nhóm.

Bàn giao quyết định loại tài liệu chính, fields/required/date/money, input limits, P0/P1 và bảng ai giữ module nào. Lập danh sách phần tái dùng từ từng branch với SHA nguồn. Đạt khi cả năm người xác nhận mình nhận gì, không còn hai schema tự xưng nguồn chuẩn; việc chưa chốt có owner và thời điểm chốt trong tuần 1. Trí và Quang review.

### TG-02 Hợp nhất nền vào main

Tuần 1, khoảng 6 giờ. Requirement ENG-01/02/03; BL-012 nền. Phụ thuộc TG-01 và kiểm tra ứng viên cùng TN-01/Q-01.

Bàn giao PR nền chung, một dependency/lock strategy và entry points; không merge mù các app trùng. Đạt khi người khác cài/chạy đúng commit, catalog/mock được gắn nhãn, kiểm tra native OCR ghi thật pass/fail, lineage phần port và kế hoạch chuyển năm nhánh rõ. Trí và Tuấn review; đây là ngoại lệ PR gom nền có kiểm soát một lần.

### TG-03 Hợp đồng dữ liệu và API chung

Tuần 2, khoảng 10 giờ. Requirement MVP-02..06, EVD-04; BL-001/006/007. Phụ thuộc TG-01.

Bàn giao schemas domain, draft/final, document/run/revision/event/export/provenance, error envelope, page/coordinate convention và examples cho hai loại tài liệu thiết kế. Sinh schemas/types, có drift checks. Đạt khi producer và consumers cùng parse ví dụ missing/invalid/unreadable/review-null, không chỉnh generated bằng tay và breaking changes có version. Quang, Trí review; Thao/Tuấn xác nhận dùng được.

### TG-04 CI và môi trường chung

Tuần 3, khoảng 10 giờ. Requirement ENG-01/03; BL-012. Phụ thuộc TG-02/03.

Bàn giao frozen install, lint/format/types/unit/contracts/build, data/evaluator và E2E phù hợp; job native OCR tách prerequisite thật. Chốt runtime theo compatibility, ưu tiên Node LTS được hỗ trợ và Python chạy engine đã chọn; không copy nguyên ba bộ pins. Đạt khi ghi run URL/head SHA hiện tại, không secrets/GPU cho checks nền, không continue-on-error, timeout/permissions hợp lý. Tuấn review.

### TG-05 Tích hợp API và quản lý thay đổi contracts

Tuần 4-6, khoảng 14 giờ. Requirement MVP-01..06, ENG-04. Phụ thuộc TG-03 và các PR của bốn người.

Bàn giao app wiring, schema registry/config và các lát cắt tích hợp vào main; giải dependency theo thứ tự, không nhúng toàn bộ logic vào main.py. Đạt khi mỗi tuần demo một hành vi mới từ main, request/response/version/error nhất quán và không có feature báo thành công giả. Trí review các thay đổi code của Tùng, không tự duyệt.

### TG-06 Docker và tái lập môi trường

Tuần 4-6, khoảng 12 giờ. Requirement ENG-01/03, NFR-01/07; BL-012. Phụ thuộc TG-04, TR-02/03 và Q-02.

Bàn giao Docker local gồm app, OCR/system dependency, models được lấy từ nguồn/hash đã chọn, volumes runtime và migration/startup policy; không secrets trong image. Đạt khi người khác chạy trên máy/checkout sạch, restart vẫn đọc dữ liệu đã lưu, health/readiness đúng và có lệnh backup/restore tối thiểu. Native/Docker nếu có phần chưa kiểm chứng phải có blocker, không đánh dấu done. Tuấn và Trí review.

### TG-07 Tích hợp các nâng cao được chọn

Tuần 7-8, khoảng 10 giờ. Requirement MVP-02/04, EVD-02/04; BL-010/011 tùy lựa chọn. Phụ thuộc cổng G3 và quyết định P1.

Bàn giao config/schema/API cho report dashboard, run comparison hoặc schema thứ hai; không tạo evaluator/UI report độc lập với run artifacts. Đạt khi mỗi P1 có owner/tests/data tương ứng, main không regression, khối lượng còn lại vừa sức trước 14/12. Trí/Tuấn review. Nếu G3 trễ, chuyển giờ này sang hoàn thiện P0.

### TG-08 Review phát hành và khóa tính năng

Chuẩn bị từ tuần 7, nghiệm thu tuần 8-9; khoảng 12 giờ. Requirement ENG-01..04, DATA-01; BL-012. Phụ thuộc G3/G4, TN-08.

Bàn giao release checklist, security/data/license review, user manual, architecture/SRS/traceability cập nhật theo code thực, backlog giới hạn còn lại. Đạt khi không còn lỗi blocker về mất dữ liệu/export sai/secret, chạy đúng commit, feature chưa làm không được quảng cáo, các nhánh tích hợp đúng thứ tự. Trí và Tuấn review.

### TG-09 Bàn giao và diễn tập

Tuần 9, tuần 10 dự phòng; khoảng 12 giờ. Requirement ENG-01/02/04, EVD-01..04; BL-012. Phụ thuộc TN-09/Q-09/TH-09; G5 là cổng xác nhận đầu ra bàn giao, không phải đầu vào để bắt đầu task.

Bàn giao main/release candidate, runbook, phân vai thuyết trình và demo có lỗi/cách phục hồi, báo cáo đúng schema/model/data/config/version. Đạt khi cả năm người tự chạy được phần chính và giải thích phần mình, có người backup module, deadline thật của giảng viên được đối chiếu. Không tạo tags/release/hosting ngoài quyền nhóm đã thống nhất. Trí review hồ sơ Tùng.

## 10 Phân công chi tiết của Quang

**Trách nhiệm:** AI/OCR/extraction thật và chất lượng prediction trước review. Code chủ yếu ở pipeline, không làm lại toàn bộ frontend/backend. Phối hợp với Tuấn nhưng không xem final-test labels để tune. Reviewer chính: Tuấn, Trí/Tùng với interfaces.

### Q-01 Khảo sát và chọn baseline OCR

Tuần 1-2, khoảng 10 giờ. Requirement MVP-01, EVD-04; BL-002. Phụ thuộc TG-01.

Bàn giao đánh giá phần Tesseract đang có, một phương án thay thế chỉ nếu cần, engine/package/weights/source/license/hash/runtime và vài output thật. Đạt khi chọn một engine chạy được trên môi trường chung, kiểm dấu Việt/số/layout/tài nguyên, không kết luận từ commit message hoặc scores fixture. Không benchmark tải model/API trả phí trong lượt lập kế hoạch này. Tuấn review protocol, Tùng chốt ADR.

### Q-02 Tiền xử lý OCR và bằng chứng tọa độ

Tuần 2-3, khoảng 10 giờ. Requirement MVP-01/02, ENG-04; BL-003. Phụ thuộc Q-01/TG-03.

Bàn giao adapter OCR thật giữ raw text/scores/spans, preprocessing có transform về ảnh gốc, model/config metadata, timeout/unavailable/failed rõ. Đạt khi thiếu engine/model fail đúng, không empty-success hoặc mock fallback, bbox/page nằm đúng frame, không đọc gold. Tests gồm ảnh rõ/nghiêng/không chữ và provider failure. Tuấn và Trí review.

### Q-03 Extraction hóa đơn theo schema chung

Tuần 2-4, khoảng 14 giờ. Requirement MVP-02, EVD-03; BL-004. Phụ thuộc TG-03, Q-02 cung cấp output chuẩn; có thể dùng contract fixtures explicit trong lúc chờ.

Bàn giao alias/nhãn, vị trí/ghép dòng, candidates, raw/normalized, evidence span IDs và abstain cho năm field. Đạt khi không hard-code theo filename/ID, không nuốt tổng tiền dòng hàng thành total tùy tiện, nhiều ứng viên mâu thuẫn để null/review, giữ số 0 và dấu theo policy. Rule/model versions có hash, tests lỗi mapping/missing/unsupported. Tuấn review, Trí kiểm integration.

### Q-04 Confidence và phối hợp normalization

Tuần 4-5, khoảng 10 giờ. Requirement MVP-03/05, EVD-04; BL-010 phần contract/policy. Phụ thuộc Q-03, TG-03, TN-04.

Bàn giao signals OCR từ spans của field, mapping/evidence/candidate reasons và method heuristic/unknown có version. Trí giữ business validator; Quang dùng đúng normalization đã chốt và không nhân đôi rules. Đạt khi không lấy điểm trung bình trang cho mọi field, không gán 0.8/90 mặc định như xác suất đúng, không ép guess trường unreadable. Unknown không bị đổi thành 0% chắc sai. Tuấn review.

### Q-05 Phân tích baseline và cải thiện có căn cứ

Tuần 4-6, khoảng 10 giờ. Requirement EVD-02/03/04; BL-009/010. Phụ thuộc Q-03/04, TN-03/04.

Bàn giao predictions trước review và run metadata; cùng Tuấn phân primary cause và các nhóm lỗi, thay đổi trên development/validation với config version mới. Đạt khi so baseline cùng split/protocol, giữ cả lỗi chưa sửa và abstentions, chốt confidence policy trên validation trước final test. Không nhận gold trong inference hoặc tune theo holdout rồi gọi độc lập. Tuấn review báo cáo, Tùng duyệt G3.

### Q-06 Schema đơn đề nghị nếu được nhận P1

Tuần 6 thiết kế, tuần 7-8 triển khai; khoảng 12 giờ. Requirement MVP-02/05; BL-001/004 mở rộng. Phụ thuộc G3, TG-03, dataset schema thứ hai của TN-02/03.

Bàn giao extractor bảy field đơn đề nghị với evidence/abstain và aliases đa layout. Đạt khi schema được chọn explicit, student_id string, request_content nhiều dòng không lẫn chữ ký, absent/unreadable đúng, không làm UI/backend viết lại toàn bộ. Có benchmark riêng có support, không dùng metrics hóa đơn đại diện. Nếu không nhận P1, giờ dùng củng cố layout/field critical của hóa đơn. Tuấn review.

### Q-07 Độ bền theo nhóm chất lượng ảnh

Tuần 7-8, khoảng 10 giờ. Requirement MVP-01/02, EVD-02/03; BL-009. Phụ thuộc Q-05, TN-06.

Bàn giao cải thiện nhỏ có ablation trên development/validation cho blur/rotation/scale/multiline; ghi công đổi accuracy/abstain/latency. Đạt khi không làm sửa ảnh mất meaning/zero/dấu, giữ transform và so đúng baseline; khó quá phải report giới hạn hoặc yêu cầu ảnh tốt hơn. Tuấn review, Tùng chọn thay đổi trước freeze.

### Q-08 Một thí nghiệm tùy chọn có giới hạn

Tuần 7-8 nếu được cả nhóm chọn; khoảng 6 giờ spike, không cam kết tích hợp. Requirement FUTURE_OPTION, EVD-02/04; BL-011. Phụ thuộc G3, Q-05 và tài nguyên/quyền đã xác nhận.

Bàn giao hypothesis từ taxonomy, config/prompt/model/snapshot/chi phí nếu có và so baseline trên tập cho phép; không tự gọi dịch vụ trả phí. Đạt khi kết luận giữ/bỏ có evidence, missing/unsupported vẫn abstain, không phá deadline. Nếu vượt timebox hoặc cần hạ tầng lớn, đóng thí nghiệm có ghi kết quả chưa đo, chuyển công sang P0/P1. Tuấn review, Tùng quyết định.

### Q-09 Đóng băng AI và bàn giao tái lập

Tuần 9, tuần 10 sửa lỗi khi cần; khoảng 8 giờ. Requirement EVD-02/03/04, ENG-01; BL-009/012. Phụ thuộc G4 và TN-06.

Bàn giao model/rules/config/locks/hashes, lệnh inference thật, hardware/latency đo thực, danh sách hạn chế và demo failure/abstain. Config đã khóa tại G4 phải được bàn giao trước khi Tuấn chạy TN-09. Đạt khi Tuấn chạy được không cần file cá nhân của Quang, không có gold leakage, báo model chất lượng trước review tách chất lượng sau review. Không sửa rules sau khi xem final test mà giữ nguyên tên run/config. Tuấn review.

## 11 Phân công chi tiết của Trí

**Trách nhiệm:** backend bảo đảm dữ liệu không mất/sai bản, API đúng contract, upload/storage/run/revision/confirm/export. Tận dụng phần repository/migration đã có; không tiếp tục viết AI thay Quang. Reviewer chính: Tùng; Thao/Tuấn phối hợp consumers/E2E.

### TR-01 Thiết kế persistence và tiếp nhận module backend

Tuần 1, khoảng 8 giờ. Requirement MVP-04/06, EVD-04; BL-005/006. Phụ thuộc field definitions sơ bộ của TG-01; đồng bộ contracts TG-03 trong tuần 2.

Bàn giao schema DB cho documents, immutable runs/predictions, revisions/events và artifact metadata; migration plan và path runtime ngoài Git. Đạt khi không dùng một JSON mutable vừa là máy vừa là review, relation/transaction/version rõ, lựa chọn SQLite local phù hợp scope. Tùng review; không chuyển PostgreSQL/MinIO chỉ vì branch cũ có tên công nghệ đó.

### TR-02 Upload và storage an toàn

Tuần 2, khoảng 12 giờ. Requirement DATA-01, MVP-01, NFR-04/07; BL-005. Phụ thuộc TG-03, TR-01.

Bàn giao multipart endpoint, kiểm magic/content/byte/pixel/page, tên file do hệ thống sinh, checksum/provenance và URL đọc ảnh qua API. Đạt khi reject file giả extension/traversal/oversize/decompression giới hạn, cleanup tạm khi lỗi, không log tài liệu mặc định và không expose path đĩa. Limit phải dùng common config. Tùng và Tuấn review.

### TR-03 Lifecycle run và gọi pipeline

Tuần 2-3, khoảng 10 giờ. Requirement MVP-01/02, EVD-04; BL-003/005. Phụ thuộc TR-02, TG-03, Q-02 theo interface.

Bàn giao tạo run/status/polling, worker local bounded, deadline/idempotency và recovery khi restart. Đạt khi failed/unavailable phân biệt, retry theo policy không nhân run ngoài ý muốn, restart không treo running vĩnh viễn hoặc mất job không báo, default real không trả mock. Không cần distributed queue. Tùng/Quang review.

### TR-04 Lưu machine output và truy vấn document

Tuần 3-4, khoảng 10 giờ. Requirement MVP-02/04, EVD-04; BL-005/006. Phụ thuộc TR-01/03, Q-03.

Bàn giao lưu machine snapshot/spans/config metadata, API đọc result/document list/status và phân trang/filter cơ bản theo scope. Đạt khi reload/restart vẫn xem đúng run, UI nhận URL/IDs không local path, các run không ghi đè lẫn nhau, metadata version thống nhất. Tùng review; Tuấn integration tests.

### TR-05 Draft review và kiểm soát revision

Tuần 4-5, khoảng 12 giờ. Requirement MVP-04/05; BL-006. Phụ thuộc TR-04, TG-03.

Bàn giao lưu draft cho thiếu/sai values kèm validation issues, revision tăng và ReviewEvents old/new/time; explicit reviewed-null. Dùng transaction/compare-and-swap với expected_revision, không chỉ check trước rồi ghi rời rạc. Đạt khi hai client/tab stale trả 409, không mất edits, sửa confirmed tạo draft mới, không bịa reviewer identity khi app chưa có accounts. Tùng và Thao review.

### TR-06 Backend confirm và export đúng bản

Tuần 5-6, khoảng 12 giờ. Requirement MVP-05/06; BL-007. Phụ thuộc TR-05 và business validation.

Bàn giao confirm persisted latest revision, validate required/calendar/cross-field; export do server tạo từ revision confirmed. Đạt khi draft/stale/invalid bị từ chối đúng mã, không tin approved hoặc final JSON client, ExportArtifact chứa IDs/schema/provenance và không path/secret/ảnh. Idempotent confirm/export đúng semantics đã chốt; tests request giả không vượt gate. Tùng/Tuấn review.

### TR-07 Chạy lại và lịch sử có truy vết

Tuần 6 phần P0, tuần 7 phần xem lịch sử P1 nếu được nhận; tổng khoảng 8 giờ. Requirement MVP-04/06, EVD-04; BL-006/007. Phụ thuộc TR-04/05/06.

Bàn giao phần P0 trước G3 cuối tuần 6: reprocess tạo run mới và giữ nguyên các run/revisions cũ. Đạt khi bản đã sửa không bị OCR mới ghi đè, export tham chiếu đúng run/revision, retry/reload không đổi lịch sử cũ. Phần tuần 7 chỉ bổ sung API xem/so sánh lịch sử thuận tiện cho P1 đã chọn. Không để điều kiện bất biến bắt buộc sang tuần 7. Tùng/Thao review.

### TR-08 Batch nhỏ nếu được chọn

Tuần 7-8, khoảng 8 giờ. Requirement P1; liên kết MVP-01/04. Phụ thuộc G3, TR-03, TH-06.

Bàn giao upload/chạy một danh sách nhỏ, giới hạn số document và concurrency theo config, trạng thái từng item và retry failed item rõ. Đạt khi không một lỗi làm cả batch thành success, không vượt storage/memory/deadline và vẫn review/confirm riêng từng document. Không thêm ZIP/PDF nhiều trang hoặc export chưa confirmed. Nếu không đủ thời gian, bỏ task này, dùng giờ cho export/recovery. Tùng/Tuấn review.

### TR-09 Độ bền storage và bàn giao backend

Tuần 8-9, tuần 10 dự phòng; khoảng 10 giờ. Requirement ENG-01, MVP-04/06, NFR-07; BL-012. Phụ thuộc TG-06, TN-08, TR-06/07; kiểm thêm TR-08 nếu nhận batch.

Bàn giao migration upgrade/test rollback khi thích hợp, backup/restore local, retention/delete policy cho runtime và error handling an toàn. Đạt khi thử restart/two tabs/retry/cleanup không mất revision hoặc xuất sai bản, cài mới không cần DB của tác giả, tài liệu API/giới hạn đúng code. Không tự xóa dữ liệu nhóm để demo cleanup. Tùng/Tuấn review.

## 12 Phân công chi tiết của Thao

**Trách nhiệm:** frontend dùng được cho workflow thật, đúng API/version/revision và giải thích AI trung thực. Code nghiệp vụ inference không viết lại trong UI. Reviewer chính: Trí; Tuấn review flows/keyboard và Tùng review common contracts.

### TH-01 Chốt luồng và tiếp nhận UI

Tuần 1, khoảng 8 giờ. Requirement MVP-04/06, ENG-04; BL-006/012. Phụ thuộc field definitions sơ bộ của TG-01; đồng bộ contracts TG-03 trong tuần 2.

Bàn giao bản đồ màn hình upload/list/status/review/history/export, wireframes có empty/loading/error và states chưa triển khai. Audit UI Tùng để dùng lại. Đạt khi mọi thao tác đều ánh xạ endpoint/response, fixture rõ nhãn, không nút thành công giả; label/keyboard focus được nghĩ trước. Trí/Tuấn review.

### TH-02 Upload và trạng thái thật

Tuần 2-3, khoảng 10 giờ. Requirement MVP-01/04, ENG-04; BL-005/006. Phụ thuộc TG-03, TR-02/03.

Bàn giao chọn schema/file, hiển thị giới hạn, gọi API upload/start run/polling và document list cơ bản. Đạt khi errors file/provider/timeout có thông điệp và retry phù hợp, không gửi hai lần do double-click, không giữ spinner vô hạn, UI không coi health đồng nghĩa OCR ready. Trí/Tuấn review.

### TH-03 Ảnh nguồn và bằng chứng

Tuần 3-4, khoảng 12 giờ. Requirement MVP-02/03/04; BL-006. Phụ thuộc Q-02/03, TR-04, TG-03.

Bàn giao ảnh nguồn/preview, chọn field highlight đúng spans, zoom cơ bản và trạng thái không evidence; raw/normalized phân biệt khi cần. Đạt khi coordinate mapping đúng scale/rotation theo contract, missing evidence không tự vẽ, confidence có giải thích chữ và không chỉ màu. Keyboard có thể chọn field; không render OCR text thành HTML tin cậy. Trí/Tuấn review.

### TH-04 Sửa xóa lưu nháp và lỗi gần trường

Tuần 4-5, khoảng 12 giờ. Requirement MVP-04/05; BL-006. Phụ thuộc TR-05, TH-03.

Bàn giao inputs theo schema, chỉnh/xóa explicit, dirty/saving/saved/error, lưu draft invalid và reload. Đạt khi xóa thành null không tự khôi phục máy, số 0 đầu không mất, warning/error khác nhau, mất mạng có retry và không báo đã lưu trước server. Có cảnh báo rời trang khi còn edits chưa lưu theo UX phù hợp. Trí/Tuấn review.

### TH-05 Conflict xác nhận và tải export

Tuần 5-6, khoảng 12 giờ. Requirement MVP-04/05/06; BL-007. Phụ thuộc TR-05/06, TH-04.

Bàn giao màn hình conflict 409 và đối chiếu trước tải lại, confirm đúng revision, nút export gọi backend artifact. Đạt khi sửa sau confirm làm draft, stale/unconfirmed/invalid không tải JSON như final, chưa đọc được required field có hướng dẫn ảnh tốt hơn, backend là authority. Không chỉ JSON.stringify form ở frontend rồi gọi hoàn thành export. Trí/Tuấn review.

### TH-06 Danh sách và lịch sử so sánh

Tuần 6-7, khoảng 8 giờ. Requirement MVP-04, EVD-04; P1. Phụ thuộc TR-04/07 và G3 cho phần nâng cao.

Bàn giao filters/status/search phù hợp dữ liệu local, lịch sử run/revision, xem giá trị máy và bản đã sửa tách nhau; so sánh run khi được chọn. Đạt khi chọn run/revision không lẫn dữ liệu giữa document, xác nhận/export luôn gắn ID đang xem và trạng thái loading/error rõ. Trí review.

### TH-07 Schema thứ hai hoặc PDF theo scope

Tuần 7-8, khoảng 10 giờ. Requirement MVP-02/04/05; P1. Phụ thuộc G3, Q-06 hoặc PDF backend đã kiểm tra, TG-03.

Bàn giao form từ field definitions/schema, labels/rules đúng loại tài liệu; preview PDF một trang nếu backend hỗ trợ. Đạt khi không dùng invoice fields cho đơn đề nghị, không hiển thị sai thang tiền/ngày/mã, loại đầu vào chưa hỗ trợ bị từ chối rõ, tests cả schemas và responsive. Nếu không nhận P1, củng cố core form và source evidence. Trí/Tuấn review.

### TH-08 Chất lượng giao diện và khả dụng

Tuần 8-9, khoảng 10 giờ. Requirement NFR-03, MVP-04; BL-012. Phụ thuộc TN-08, TH-05/06/07 đã nhận.

Bàn giao keyboard navigation, focus/error summary, labels/aria, responsive, save/conflict/retry polish và các trạng thái lỗi dễ hiểu. Đạt khi thao tác chính dùng được bàn phím, không tràn viewport đã chọn, không dựa riêng màu để giải nghĩa confidence; không có stack/path nội bộ hiện cho người dùng. Tuấn review và ghi các viewport/case thực đã thử.

### TH-09 Demo giao diện và hướng dẫn sử dụng

Tuần 9, tuần 10 dự phòng; khoảng 8 giờ. Requirement ENG-01/04, MVP-04/06; BL-012. Phụ thuộc G4 và TN-09; G5 là cổng nghiệm thu đầu ra.

Bàn giao user guide, ảnh/chạy demo luồng thật với sample được phép, giải thích confidence/review/export và failure recovery. Đạt khi demo khớp đúng commit/API/current report, không dùng fixture như model output, người khác có thể tự thao tác. Tùng/Tuấn review; không tự publish site hoặc gửi dữ liệu ra dịch vụ ngoài.

## 13 Phân công chi tiết của Tuấn

**Trách nhiệm:** dữ liệu và đo lường đáng tin, system/E2E tests, bằng chứng phục vụ release. Không phụ trách thay mọi unit tests của thành viên. Reviewer chính: Quang; Tùng review workflow và Trí/Thao review ca nghiệp vụ.

### TN-01 Kiểm tra nền và các evaluator cũ

Tuần 1-2, khoảng 8 giờ. Requirement ENG-03/04, EVD-02; BL-009 nền. Phụ thuộc khảo sát/TG-01.

Bàn giao bảng audit công thức/provenance/null/unreadable của các nhánh, cùng Tùng kiểm install/contracts/tests của nền ứng viên. Đạt khi kết quả mới chạy tách khỏi test counts/metrics tác giả nhánh từng công bố, không dùng README như chứng minh chất lượng, nêu metric nào cần port/sửa. Quang review.

### TN-02 Dataset và generator theo scope

Tuần 1-4, khoảng 12 giờ. Requirement DATA-01, EVD-01/03/04; BL-008. Phụ thuộc field definitions sơ bộ TG-01 để mở generator/protocol tuần 1; đồng bộ TG-03, TH-01 và thông tin engine Q-01 trước khi khóa dataset.

Bàn giao generator/sources/license/font/template metadata, visible-image gold, nhiều layout và các ca clear/zero/dấu/multiline/absent/invalid/unreadable; mở dataset schema thứ hai chỉ nếu nhận P1. Đạt khi ảnh đọc được và gold phản ánh ảnh, không lưu bí mật bị che, mỗi mẫu có parent/template/version/checksum/quality tags. Quang/Thao review chéo một phần; không Tuấn tự gán nhãn rồi tự xác nhận độc lập.

### TN-03 Chia tập và review nhãn độc lập

Tuần 2-3, duy trì đến freeze; khoảng 10 giờ. Requirement EVD-01, DATA-01; BL-008. Phụ thuộc TN-02.

Bàn giao manifest chia parent trước biến thể, development/validation/final-test, duplicate/content/template audit và label-review log. Đạt khi không parent overlap, model code không thấy gold, test labels không dùng chỉnh rules; mẫu cũ từng xem/tune được đánh dấu phù hợp, không đổi tên thành test độc lập. Giải quyết bất đồng bằng ảnh và guideline có version. Quang review protocol; Tùng/Trí/Thao tham gia đối chiếu nhãn.

### TN-04 Evaluator chuẩn và run metadata

Tuần 2-4, khoảng 12 giờ. Requirement EVD-02/03/04; BL-009. Phụ thuộc TG-03, TN-01/03.

Bàn giao metric chính giữ dấu/zero/types, present accuracy, PRF/counts/support, extra-fill absent, unreadable abstention, document exact match/exclusions, micro/macro/null denominators; confidence buckets khi có thật. Đạt khi test 50 present/48 non-null/45 đúng cho TP45 FP3 FN5, wrong non-null tính FP+FN, không tính null-null thành TP; có report_type/source và run/dataset/config/lock/hash. Quang review.

### TN-05 Kiểm thử API và workflow thật

Tuần 3-6, khoảng 10 giờ. Requirement MVP-01..06, ENG-03; BL-005/006/007. Phụ thuộc các API/UI tương ứng; thêm dần sau mỗi PR.

Bàn giao integration/E2E dùng engine thật ít nhất happy path và cases invalid/missing/clear-null/reload/409/reprocess/export stale/provider unavailable. Đạt khi kiểm nội dung JSON tải về so revision lưu, không chỉ assert có nút/download; backend restart và hai tabs có tests, mock UI tests không được gọi là AI E2E. Trí/Thao review.

### TN-06 Baseline và confidence trên validation

Tuần 4-6, khoảng 10 giờ. Requirement EVD-02/03/04, MVP-03; BL-009/010. Phụ thuộc Q-03/04/05, TN-03/04.

Bàn giao baseline report máy trước review, error records/cause counts không cộng trùng, slices layout/quality, support/confidence/abstain và runtime. Đạt khi chỉ chọn policy/threshold trên validation, không bịa target chất lượng từ fixtures, có căn cứ để chốt regression/ship criteria tuần 3-4 rồi version/freeze trước final test. Quang review, Tùng duyệt quyết định.

### TN-07 Dữ liệu cho dashboard chất lượng

Tuần 7-8, khoảng 10 giờ. Requirement EVD-02/03/04; P1. Phụ thuộc G3, TN-06, TG-07.

Bàn giao report artifacts/schema cho so sánh runs, field accuracy/support/abstain, taxonomy và config/version. Đạt khi UI dùng report đã truy vết, không tính lại metric bằng công thức frontend, không expose secrets/gold final-test vào inference hoặc UI công khai. Nếu chưa nhận dashboard, dùng giờ cho label QA và regression suite. Quang/Tùng review.

### TN-08 Regression và kiểm tra môi trường

Tuần 7-8, khoảng 10 giờ. Requirement ENG-01/03, NFR-01/03/07; BL-012. Phụ thuộc TG-06, TR-06 và TH-05.

Bàn giao clean install/Docker checks, upload abuse/limits, browser/keyboard/responsive cases, restart/recovery/cleanup, performance measurement có hardware/cold-warm. Kết quả kiểm tra này là đầu vào cho TR-09/TH-08 sửa, không chờ hai task sửa xong mới bắt đầu kiểm. Đạt khi lỗi có owner/repro/severity và regression test, không bỏ check để xanh, dependency/model/runtime changes có evidence đúng SHA. Tùng/Trí review.

### TN-09 Final test độc lập và hồ sơ evidence

Tuần 9, tuần 10 chạy lại khi có lý do; khoảng 8 giờ. Requirement EVD-01..04, ENG-04; BL-009/012. Phụ thuộc G4, Q-09 và candidate commit từ TG-08.

Bàn giao sealed-test report và predictions trước review, manifest/hash/config/commit/dirty/runtime, hạn chế, taxonomy/examples và checklist bốn evidence; đây là đầu vào cho TG-09 bàn giao cuối cùng. Đạt khi dữ liệu test độc lập với tuning, mẫu số/support/exclusions minh bạch, code/config sau test đổi phải run ID mới và ghi nếu test đã được dùng debug. Thí nghiệm sau review nếu có phải tách riêng, không bịa người/thời gian tiết kiệm. Quang review phương pháp, Tùng review hồ sơ bàn giao.

## 14 Khối lượng và cách quản lý thời gian

Thông tin đã xác nhận là mỗi người 2-3 giờ/ngày. Kế hoạch dùng mức thận trọng 6 ngày/tuần, 2 giờ/ngày; ngày còn lại nghỉ hoặc bù việc, không mặc định bắt buộc làm đủ 7 ngày. Như vậy có khoảng 12-18 giờ/người/tuần, tổng 600-900 giờ nhóm trong 10 tuần. Không coi mức 3 giờ và toàn bộ 7 ngày đều là năng lực chắc chắn.

| Thành viên | Task tập trung ước lượng | Review và phối hợp | Buffer học sửa lỗi | Tổng dùng để lập kế hoạch |
| --- | --- | --- | --- | --- |
| Tùng | 90 giờ | 15 giờ | 15 giờ | 120 giờ |
| Quang | 90 giờ | 15 giờ | 15 giờ | 120 giờ |
| Trí | 90 giờ | 15 giờ | 15 giờ | 120 giờ |
| Thao | 90 giờ | 15 giờ | 15 giờ | 120 giờ |
| Tuấn | 90 giờ | 15 giờ | 15 giờ | 120 giờ |
| Cả nhóm | 450 giờ | 75 giờ | 75 giờ | 600 giờ |

Task hours là dự toán để phát hiện lệch tải, không thời gian thực đã đo hoặc quota đánh giá cá nhân. Một số task P1/P2 có điều kiện; nếu không nhận thì dùng cùng giờ củng cố core, không tính chồng thành năng lực thêm. Khi báo task sắp quá dự toán, chia nhỏ/cắt scope/nhờ review; không giấu đến tuần cuối. Hai tuần đầu đo throughput thật để hiệu chỉnh lịch. Riêng tuần 1, Tùng chỉ cam kết khoảng 10 giờ TG-01/TG-02 và dùng field definitions sơ bộ để nhóm bắt đầu; TG-03 chi tiết ở tuần 2, TG-04 CI đầy đủ ở tuần 3. Tránh nhồi một tuần vừa gom nền, hoàn tất contracts và dựng mọi CI. Tuần 2-5 có thể cần mức gần 3 giờ/ngày cho backend/UI, phải báo sớm nếu không đáp ứng; giảm P1 trước khi đẩy core sang tuần cuối.

Mỗi buổi 2 giờ có thể chia khoảng 10 phút cập nhật main/issue, 80 phút tập trung code/data, 20 phút tests/review, 10 phút commit/evidence. Ba buổi một tuần có sync ngắn tối đa 15 phút khi cần dependency; một buổi demo/review tuần khoảng 45 phút. Giờ họp cố định do nhóm chốt, không tự tạo lịch hay gửi thông báo.

## 15 Kế hoạch dữ liệu và đánh giá chất lượng

### 15.1 Golden dataset có thể kiểm tra

Mục tiêu lập kế hoạch đề xuất cho hóa đơn là khoảng **150 parent documents độc lập**, ví dụ 90 development, 30 validation, 30 final-test; không phải quy định giảng viên hoặc số lượng đã có. Chốt quy mô khả thi ở tuần 2 sau khi đo tốc độ tạo/kiểm nhãn. Dataset 30 mẫu đã tồn tại ở nhánh Tùng và 6 fixture của Quang có thể phục vụ development/contract; mẫu từng dùng xem/sửa rules không được gọi lại là test độc lập.

Đề xuất ít nhất ba layout development, và nếu muốn nói về layout chưa thấy thì dành một layout riêng trong final-test, báo kết quả riêng với support. Tạo biến thể clear/blur/rotate/crop sau khi chia parent, cùng parent cùng split. Không đếm nhiều biến thể của một parent như nhiều tài liệu độc lập khi diễn giải độ chắc chắn. Schema thứ hai nếu nhận P1 có dataset/metrics riêng; quy mô nhỏ phải ghi hạn chế, không mượn accuracy hóa đơn.

Manifest có sample_id, parent_document_id, template_id, document_type, input/annotation paths + hashes, split, quality tags, provenance, dataset_version. Gold present/absent/unreadable phản ánh ảnh; identifiers giữ 0, Unicode giữ dấu; gán lại nhãn sau crop/blur làm mất nội dung. Labels cuối do người khác đối chiếu ảnh và log bất đồng; Tuấn điều phối, bốn người còn lại luân phiên review, không cần ai chỉ làm nhập nhãn toàn dự án.

### 15.2 Metrics và quy tắc quyết định

Metric chính là exact match theo field trên gold present/readable sau normalization chốt trước; PRF trên tuples document-field-value non-null, wrong non-null vừa FP vừa FN; absent extra-fill rate và correct abstention riêng; unreadable loại value matching chính nhưng báo abstention/support. Document exact match có support/exclusions; micro cộng counts, macro chỉ fields có denominator xác định, zero denominator null + lý do. Confidence buckets kèm method/support/accuracy, không tự xem score là calibrated probability.

Nếu cần metric null-inclusive từ nhánh cũ, giữ tên riêng và không dùng thay accuracy present/readable. CER/WER chỉ hỗ trợ phân tích OCR, không thay field mapping metrics. Tất cả model metrics dùng prediction trước review; quality sau review hoặc thời gian người dùng là nghiên cứu riêng. Không dùng giá trị người dùng đã sửa để làm kết quả model đẹp hơn.

Không đặt accuracy 95% hoặc latency P95 tùy tiện rồi gọi yêu cầu gốc. Tuần 3-4 lấy baseline thật trên development/validation, thống nhất tiêu chí chất lượng/regression với field critical, risk và phần cứng; freeze trước final test. Mục tiêu nghiệp vụ an toàn là người dùng phát hiện/sửa được và backend từ chối bản chưa confirmed/invalid/stale; độ đúng AI phải báo thực. Confidence chưa đủ bằng chứng có thể unknown; không cần VLM để hoàn thành đề tài.

### 15.3 Version và report mỗi lần chạy

Run lưu commit + dirty, dataset/split/manifest hash, engine package khác weights revision/hash, rules/prompt/config/schema/normalization/validation/confidence/evaluator versions, resolved config đã loại secrets, locks/runtime/hardware/seed khi có, prediction/report paths và status. Đo latency chỉ pipeline thật, nêu cold/warm; API model không pin snapshot phải ghi hạn chế tái lập. Không key/signed URL/source text không cần thiết trong artifact.

Tuấn lưu report/evidence, Quang chịu trách nhiệm model metadata, Tùng chốt release manifest. Lần thử mới có run ID mới; sửa rules sau nhìn test phải ghi contamination và tổ chức đánh giá độc lập phù hợp, không giấu bằng đổi tên test.

## 16 Ma trận kiểm thử và nghiệm thu

| Case bắt buộc | Kết quả cần chứng minh | Owner triển khai và kiểm tra |
| --- | --- | --- |
| Happy path thật | Upload → OCR/extract → persisted review → confirm → server export; JSON đúng revision | Trí/Thao/Quang; Tuấn E2E |
| Thiếu hoặc sai required field | Draft lưu được kèm issues; confirm/export cuối bị chặn đúng lỗi | Trí/Thao; Tuấn |
| Xóa thành null | Reload vẫn null đã review, không fallback machine | Trí/Thao; Tuấn |
| Hai tab revision cũ | Save/confirm/export stale trả 409; UI đối chiếu, không mất sửa | Trí/Thao; Tuấn |
| Re-OCR | Run mới bất biến, review cũ vẫn tồn tại, export tham chiếu đúng run | Quang/Trí; Tuấn |
| Provider missing/timeout/failure | Readiness/status/error thật, không empty success hoặc fixture fallback | Quang/Trí; Tuấn |
| File không hợp lệ | Magic/bytes/page/pixel/path/temporary cleanup kiểm thực, không chỉ extension | Trí; Tuấn |
| Evidence/geometry | Highlight đúng page/scale/transform, thiếu evidence không bịa bbox | Quang/Thao; Tuấn |
| Normalization/validation | Dấu Việt, zero ID, ngày tồn tại/năm nhuận, liên trường, số tiền chính xác | Quang/Trí; Tuấn |
| Data/evaluator | Split parent/duplicates, no gold inference, present/absent/unreadable và TP/FP/FN đúng | Tuấn; Quang review |
| Restart/clean install | Persistence còn, recovery không treo, locks/models/hash/checks tái lập | Trí/Tùng; Tuấn |
| UI lỗi/keyboard/responsive | Có labels/focus/save status/retry, không mất edits, không phụ thuộc màu | Thao; Tuấn |

Unit tests do module owner viết; contract/integration tests ở ranh giới; E2E khi có workflow thật. Mock dùng unit/component tests có nhãn, không model benchmark. CI foundation không key/GPU, native OCR job prerequisites thật và không đánh dấu skipped thành passed quality. Không dùng coverage/số test/số commit tùy ý thay thế acceptance criteria.

Definition of Ready của task: problem/scope/requirements/inputs/outputs/dependencies/acceptance/owner/reviewer rõ. Definition of Done: hành vi thật đạt, tests phù hợp pass, docs/contracts/version/evidence đồng bộ, không secret/dữ liệu trái phép và được reviewer khác xác nhận. Task hoàn thành cục bộ nhưng chưa merge/test chung chỉ được ghi implemented hoặc ready-for-review, chưa gọi delivered.

### 16.1 Điều kiện nghiệm thu sản phẩm cuối trên main

Sản phẩm chỉ được ghi nhận bàn giao khi các điều kiện dưới đây cùng đạt trên một candidate commit đã tích hợp; không ghép kết quả tốt của các nhánh hoặc các config khác nhau để tuyên bố hoàn thành.

1. Toàn bộ P0 đã merge vào main, không còn module chạy riêng hoặc bước chép file thủ công giữa năm máy. Backend, frontend, pipeline và evaluator dùng đúng versions/contracts/locks trong release manifest.
2. Một thành viên không phải tác giả làm clean install và chạy được theo runbook; môi trường native và Docker đã chọn có kết quả thực. Prerequisite chưa đáp ứng phải được xử lý trước ký nghiệm thu, không đánh dấu skipped như passed.
3. Tuấn chạy E2E thật từ ảnh sample được phép qua OCR/extraction đến review/sửa/lưu/reload/confirm/export; đối chiếu JSON tải về với revision persisted. Ma trận ở mục 16 đạt, đặc biệt reviewed-null, hai tab, reprocess, restart và provider failure.
4. Không còn lỗi blocker: mất dữ liệu, xuất sai run/revision, vượt confirm/validation gate, gold leakage, secret hoặc báo success giả. Lỗi còn lại được ghi severity, repro, ảnh hưởng và cách xử lý; Tùng cùng owner thống nhất có chấp nhận được trong phạm vi đã chốt hay không.
5. Bốn evidence EVD-01..04 có đường dẫn thật và lệnh tái lập; model report là prediction trước review, có support/exclusions, dataset/config/hash và đúng code tương thích với candidate. Mọi sửa ảnh hưởng model/data/evaluator sau lần đo phải chạy lại và ghi tính độc lập của test.
6. P1 đã nhận phải hoàn tất cả backend/pipeline/UI/data/tests liên quan. Nếu không đạt thì gỡ khỏi release scope hoặc tắt rõ trước freeze và cập nhật tài liệu; không để một màn hình nửa vời làm lỗi core. P2 không phải điều kiện đỗ MVP.
7. README, hướng dẫn cài/chạy, user guide, kiến trúc/API, báo cáo chất lượng/giới hạn và kịch bản demo khớp sản phẩm. Tài sản/quyền sử dụng, model/config nguồn và dữ liệu runtime được quản lý đúng chính sách.
8. Tuấn ghi biên bản checks/evidence; Quang xác nhận pipeline/config; Trí xác nhận persistence/export; Thao xác nhận UI; Tùng cùng reviewer Trí chốt G5 và danh sách bàn giao. Mỗi người diễn giải được phần mình và có người backup chạy được. Việc ký nhận là kết quả kiểm tra thực ở tuần 9, chưa được coi là đã đạt trong tài liệu kế hoạch này.

### 16.2 Truy vết yêu cầu đến đầu ra nghiệm thu

| Yêu cầu | Task chịu trách nhiệm chính | Evidence phải có khi bàn giao |
| --- | --- | --- |
| MVP-01 OCR | Q-01/02, TR-02/03, TN-05 | Output engine thật, spans/provenance, tests provider/timeout và run tái lập |
| MVP-02 extraction | TG-03, Q-03, TR-04, TH-03 | Field definitions/contracts, predictions và evidence vùng nguồn, tests mapping |
| MVP-03 confidence | Q-04/05, TN-06 | Policy/method/version/reasons, validation report theo bucket/support hoặc unknown được giải thích |
| MVP-04 review/sửa | TR-05/07, TH-04/05, TN-05 | Tests lưu/reload/xóa-null/conflict/run bất biến và UI đối chiếu chạy thật |
| MVP-05 validation | TG-03, TR-05/06, TH-04/05 | Tests types/calendar/liên trường; draft invalid lưu được, final invalid bị chặn |
| MVP-06 export | TR-06, TH-05, TN-05 | JSON từ server đúng persisted confirmed revision, tests stale/unconfirmed/invalid |
| DATA-01, EVD-01 | TN-02/03, TG-08 | Dataset card, nguồn/quyền, manifest/hashes/splits và label-review log |
| EVD-02, EVD-03 | TN-04/06/09, Q-05/09 | Evaluator đã kiểm công thức, report model trước review, taxonomy/error records có run IDs |
| EVD-04 | TG-03/09, Q-09, TN-09 | Model/config/schema/data/evaluator versions/hashes và release/run manifests |
| ENG-01, ENG-03 | TG-04/06, TN-05/08 | Frozen install, CI đúng SHA, build/tests và clean native/Docker evidence |
| ENG-02, ENG-04 | TG-01/02/05/08/09, cả nhóm | Ownership/task/PR/review thực, nhật ký tích hợp, docs/capabilities trung thực và biên bản nghiệm thu |

## 17 Rủi ro và quy tắc xử lý chậm

| Tình huống hoặc trigger | Cách xử lý | Người điều phối |
| --- | --- | --- |
| Chưa thống nhất nền sau 48 giờ | Timebox, dùng fallback foundation và port module đạt tests; không tiếp tục ba app riêng | Tùng + cả nhóm |
| OCR/runtime không tương thích | Giữ baseline khả thi, pin nguồn/weights; chỉ tách process khi cần ADR; không mua GPU/API để né quyết định | Quang + Tùng |
| G2 không có lát cắt thật tuần 3 | Dừng provider mới/mở rộng; ghép Quang-Trí-Thao xử lý interface trước | Tùng |
| G3 chưa đạt cuối tuần 6 | Hủy nhận P1/P2 mới, đưa giờ nâng cao sang core/revision/export/evidence | Tùng + Tuấn |
| Người bận hơn 2 ngày hoặc task kẹt dependency hơn 1 buổi | Báo issue/sync, bàn giao context và backup; không sửa lén file module người khác | Owner + reviewer |
| Merge conflict/lock/schema lặp | Owner common file điều phối một PR, regenerate outputs/lock bằng tool, chạy lại consumers | Tùng |
| Test leakage/nhãn sai | Dừng công bố metric, sửa version/labels/protocol, tạo test độc lập khi cần | Tuấn + Quang |
| Export stale/mất dữ liệu | Block release, fix và thêm regression; không gọi demo hoàn chỉnh khi còn lỗi này | Trí + Tuấn |
| API/cloud chi phí/quyền dữ liệu chưa có | Không dùng dịch vụ đó; local baseline vẫn là đường hoàn thành | Tùng + Quang |
| Thêm feature sát tuần 9 | Ghi backlog sau release, không đánh đổi P0/đo độc lập/diễn tập | Tùng |

Không có cam kết triệt tiêu mọi conflict, mọi bug hay bảo đảm accuracy trước đo. Kế hoạch này làm trách nhiệm và điểm tích hợp rõ để phát hiện sớm và giới hạn ảnh hưởng.

## 18 Checklist bốn mươi tám giờ đầu

1. Tùng mở buổi chốt scope/roles/branches, điền handle thật và thống nhất core hóa đơn hay quyết định khác có lý do; xác nhận deadline thực của giảng viên nếu đã có.
2. Mỗi người gửi branch/head SHA, phần đã chạy thật, phần mock, lệnh tests và phần muốn giữ; Tuấn xác nhận nhánh của mình. Không gửi secret hoặc data không được phép.
3. Tùng/Tuấn kiểm ứng viên nền; Quang kiểm OCR/model; Trí kiểm missing persistence/export; Thao kiểm UI/API. Bàn giao quyết định nền và các gaps có evidence.
4. Tùng lập PR gom nền cùng interfaces/field definitions sơ bộ; cả nhóm review và đồng bộ năm nhánh về main chung, giữ lịch sử phần cũ. Contracts chi tiết TG-03 bàn giao đầu tuần 2, không đòi làm xong mọi API trong 48 giờ.
5. Tùng và Tuấn chuyển 45 task IDs trong kế hoạch thành issue thật nếu nhóm muốn, giữ IDs TG/Q/TR/TH/TN trong title/body và map BL requirements. Không coi các ID local là GitHub issue number đã tồn tại.
6. Mỗi task có owner/reviewer/week/dependency/acceptance và trạng thái Todo/In progress/Blocked/Review/Done; tối đa một task code chính active mỗi người.
7. Chốt giờ demo tuần, review response và cách báo blocker; chạy lát cắt đầu tiên trên main, không chỉ trình bày cây thư mục.

## 19 Mẫu giao việc gửi cả nhóm

Từ tuần 20/10 nhóm thống nhất cùng phát triển một sản phẩm AI-02. Tùng phụ trách kiến trúc/contracts/tích hợp và phát hành; Quang phụ trách AI/OCR/extraction/confidence; Trí phụ trách backend/storage/revision/export; Thao phụ trách frontend/review; Tuấn phụ trách dữ liệu/evaluation/system tests/evidence. Mỗi người có một nhánh cá nhân chính và owner module rõ. Các phần đã có sẽ được audit, dùng lại và port qua PR; không tiếp tục tự khởi tạo toàn bộ dự án.

Tuần 1 chọn nền và chốt schema/limits/API, cuối tuần 3 có lát cắt OCR thật, cuối tuần 6 đạt P0 upload tới export từ revision lưu, tuần 7-8 làm nâng cao đã chọn, tuần 9 bàn giao trước 21/12, tuần 10 dự phòng đến 28/12. Mỗi người dành 2-3 giờ/ngày theo khả năng đã xác nhận, cập nhật task và đưa phần hoàn thành vào main trong tuần. Không đợi cuối kỳ mới merge. Xin mỗi người xác nhận branch, vai trò, task đầu tiên và blocker tại buổi nhận việc.

Đây là nội dung để người dùng gửi nhóm; chưa có tin nhắn, issue assignment hay lời mời nào được gửi tự động.

## 20 Nguồn đối chiếu và trạng thái áp dụng

Nguồn yêu cầu dự án là scope/SRS/use cases/contracts/ADR và các nguyên tắc trong file foundation ban đầu; phân loại COURSE_REQUIRED/FOUNDATION_REQUIRED/PROVISIONAL/FUTURE_OPTION được giữ. Yêu cầu mới của người dùng bổ sung nhóm 5 người, Tùng làm nhóm trưởng, Quang mạnh AI, thời lượng 2-3 giờ/ngày và lịch 9-10 tuần. Phạm vi sản phẩm cuối, roles còn lại, lựa chọn nền, branch Tuấn và các P1 là đề xuất có nơi xác nhận; không bịa năng lực của Trí/Thao/Tuấn hoặc quyết định giảng viên.

Khảo sát repo được ghi riêng tại [branch audit](../reports/branch-audit-2026-10-20.md). Không chạy lại toàn bộ các nhánh khác hoặc xác nhận các con số benchmark/test trong README của tác giả. Không sửa app/schema/CI runtime, tạo remote issue/PR, gửi phân công, merge/reset/force-push/đổi remote hoặc triển khai dịch vụ trong lượt lập kế hoạch này. Những thao tác Git được mô tả là hướng dẫn để nhóm làm sau khi duyệt.

Tham khảo kỹ thuật đã đối chiếu ngày 20/10/2026: [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow) cho PR/review và lát cắt nhỏ; [GitHub merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github) cho hệ quả merge/squash; [git merge](https://git-scm.com/docs/git-merge) cho đồng bộ và conflict; [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) cho review/checks và giới hạn gói; [Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use) cho CI; [Node releases](https://nodejs.org/en/about/previous-releases) cho lựa chọn LTS; [Tesseract data files](https://tesseract-ocr.github.io/tessdoc/Data-Files.html) và [PaddleOCR installation](https://www.paddleocr.ai/main/en/version3.x/installation.html) cho spike OCR. Đây là nguồn hỗ trợ, không rubric mới hoặc kết quả engine đã đo.
