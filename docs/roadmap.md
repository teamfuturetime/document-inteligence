# Roadmap phát triển cá nhân

## Cách thực hiện

Giai đoạn 0 và S1.1 đã hoàn thành; lượt S1.2 chỉ khởi tạo frontend.
Mỗi task là một đơn vị độc lập có phạm vi,
cách triển khai, kiểm tra và commit Conventional Commits trên `tuannguyen`.
Không push, PR, merge, reset, force-push, xóa branch hoặc amend khi chưa có yêu cầu riêng.
Trước mỗi task kiểm tra branch, status, commit gần nhất và code liên quan.
Không ghi đè thay đổi có sẵn. Chỉ stage file thuộc task, xem diff và kiểm tra status sau commit.

Trạng thái task: **chưa triển khai**, **đang triển khai**, **đã triển khai**, **đã kiểm thử**.
Hoàn thành task còn cần commit local thành công; kiểm thử task nhỏ không có nghĩa cả giai đoạn
hay toàn bộ yêu cầu liên quan đã hoàn thành.

## Các task

| Task / mục tiêu | Phạm vi file dự kiến | Cách triển khai | Điều kiện hoàn thành và kiểm tra | Trạng thái |
| --- | --- | --- | --- | --- |
| S0 — Khảo sát, ghi yêu cầu và kế hoạch | `README.md`, `docs/{repository-audit,requirements,architecture,roadmap}.md` | Đọc Git/tree/code remote và công cụ local; ghi nhận bằng chứng, phạm vi, quyết định còn mở. | Kiểm tra liên kết nội bộ và đủ R01–R12; `git diff --check`; review diff; commit tài liệu, status sạch. | Đã kiểm thử (tài liệu) |
| S1.1 — Backend và health-check | `backend/app/{__init__,main}.py`, `backend/tests/test_health.py`, dependency/config backend, `.gitignore`, README, `docs/testing.md` | FastAPI tối thiểu, `GET /health`; venv/pip, khóa dependency sau kiểm tra tương thích. | Hai test offline đạt; Uvicorn trả HTTP 200 và JSON đúng; `pip check` đạt. Lệnh và bằng chứng trong `docs/testing.md`. | Đã kiểm thử |
| S1.2 — Frontend chạy local | `frontend/`, `.gitignore`, README, tài liệu kiến trúc/kiểm thử/trạng thái | React/TypeScript/Vite, trang giới thiệu tối thiểu; không dựng review UI trước. | `npm ci --offline`, typecheck/build, HTTP dev/preview và render React đạt; khóa dependency, ghi lệnh chạy local. Chưa kiểm tra trực quan do công cụ trình duyệt không khả dụng; xem `docs/testing.md`. | Đã kiểm thử (CLI/HTTP/render); còn kiểm tra trực quan |
| S2.1 — Chốt hóa đơn và schema | `backend/app/schemas/`, `backend/tests/test_schemas.py`, `docs/requirements.md` | Chốt trường, required/null, kiểu tiền/ngày và schema version; Pydantic là nguồn chính. | Test hợp lệ, thiếu trường, sai kiểu, extra key, ngày không tồn tại; không cần AI. | Chưa triển khai |
| S2.2 — Business validation | `backend/app/services/validation.py`, `backend/tests/test_validation.py` | Chuẩn hóa rõ quy tắc và trả lỗi theo trường; tách draft khỏi dữ liệu cuối. | Test chuỗi trống, số 0, tiền âm, tiền nhập nhằng, Unicode, currency sai; không tự sửa dữ liệu nhập nhằng. | Chưa triển khai |
| S3.1 — Pipeline contract và fake | `backend/app/providers/`, `backend/app/services/pipeline.py`, tests tương ứng, kiến trúc | Interface OCR/extraction nhỏ, fake có nhãn; tách các result và run metadata. | Test luồng offline, output sai schema, provider lỗi và timeout; metadata không thiếu version; không API key. | Chưa triển khai |
| S3.2 — OCR thật trên ảnh mẫu | OCR adapter, mẫu tối thiểu và manifest trong `data/`, tests OCR, tài liệu OCR | Đo ứng viên trên dữ liệu tổng hợp, chọn và ghi license/config/model version; tích hợp qua interface. | Nhận dạng ảnh thực sự; test Unicode, ảnh hỏng, không có text và timeout; báo cáo riêng test fake/real. | Chưa triển khai |
| S3.3 — VLM thật và confidence | Extraction adapter, tests extraction, cấu hình prompt/model, tài liệu provider | Chọn model theo môi trường/quyền dùng/chi phí; ảnh + OCR + schema → fields; kiểm tra output, ghi provenance và chính sách confidence. | Ví dụ inference thật từ ảnh mẫu; test fake cho JSON lỗi, thiếu trường, timeout; confidence null nếu chưa có cơ sở; model/prompt/config version đầy đủ. | Chưa triển khai |
| S4.1 — Upload tới pipeline | Backend route và file validation, `frontend/src/` upload/API client, tests | PNG/JPEG một trang, giới hạn byte/pixel, kiểm tra nội dung, file tạm, trạng thái chờ/lỗi. | API test file sai loại/quá lớn/hỏng, test chọn/gửi file và UI lỗi; chứng minh pipeline nhận đúng ảnh; dọn file tạm. | Chưa triển khai |
| S4.2 — Review/edit từng trường | Frontend review/preview, type contract và tests | Giữ extraction gốc, bản sửa độc lập; hiển thị evidence/confidence có nguồn và cảnh báo. | Test sửa từng trường, giữ giá trị gốc, trường null, nhập chưa hợp lệ, reset xác nhận sau sửa; contract khớp backend. | Chưa triển khai |
| S4.3 — Validate bản review | Backend validation API, frontend validation flow, API/UI tests | Dùng lại service S2.2; hiện lỗi theo trường, chỉ xác nhận payload đang hợp lệ. | Test lỗi backend hiện đúng; sửa sau validation vô hiệu hóa xác nhận cũ; không bỏ qua validation backend. | Chưa triển khai |
| S4.4 — Export JSON và demo luồng chính | Backend export route/service, frontend download, tests và hướng dẫn demo | Validate lại payload cuối, yêu cầu xác nhận, xuất dữ liệu sửa kèm provenance và version. | Test từ chối chưa hợp lệ/chưa xác nhận, lỗi tạo/tải file, JSON đúng Unicode/giá trị sửa; E2E upload → review → validate → export với fake. | Chưa triển khai |
| S5.1 — Golden dataset | `data/golden/`, manifest, hướng dẫn annotation và kiểm tra data | Bộ nhỏ tổng hợp có ground truth; nguồn/quyền dùng/hash/version, tách tuning/evaluation. | Kiểm tra schema/hash/ID; rà soát ảnh so với ground truth; có biến thể khó và trường thiếu, không lộ gold vào provider. | Chưa triển khai |
| S5.2 — Metrics, taxonomy và báo cáo | `evaluation/`, tests metrics/report, `docs/evaluation.md` | Field exact match và PRF theo định nghĩa yêu cầu; phân loại lỗi; report gắn dataset/model/config/code version. | Test phép tính bằng ví dụ tính tay, null/null, mẫu số 0; CLI tạo report chạy lại được; tách fake baseline với kết quả AI thật. | Chưa triển khai |
| S6.1 — Kiểm chứng và demo | Tests luồng chính/biên, README, `docs/testing.md`, demo và báo cáo giới hạn | Chạy kiểm tra tổng thể, thử bản checkout sạch với dependency đã khóa; demo fake và real phân biệt rõ. | Backend/frontend tests, build và E2E đạt; chạy theo README ở checkout sạch; evaluation có báo cáo; cập nhật trạng thái dựa trên bằng chứng. | Chưa triển khai |

S1.1 dùng commit message `feat: add backend health check`.
S1.2 dùng commit message `feat: initialize React frontend`.
Task tiếp theo theo roadmap là **S2.1**; chưa bắt đầu trong lượt S1.2.
Kiểm tra trực quan frontend vẫn còn mở, không xem typecheck/build là thay thế việc đó.
Các commit sau đặt theo phạm vi thực tế, không theo số lượng task. Nếu một task lớn hơn dự kiến,
tách phần độc lập kiểm tra được và cập nhật roadmap trước khi mở rộng.

## Điều kiện hoàn thành từng giai đoạn

- **0:** khảo sát, tài liệu được kiểm tra và commit; không tạo ứng dụng.
- **1:** backend/frontend chạy theo hướng dẫn, health-check HTTP hoạt động, test cơ bản và build đạt.
- **2:** schema/business validation có test tự động, không phụ thuộc AI.
- **3:** pipeline chạy mẫu với OCR và VLM thật, lỗi/result rõ ràng, model/config version đầy đủ;
  bộ test fake vẫn chạy offline. Test fake không thay kết quả tích hợp thật.
- **4:** trình diễn upload → extraction → review/edit → backend validation → xác nhận → JSON export.
- **5:** golden dataset, metrics/taxonomy và script tạo báo cáo có thể chạy lại, ghi rõ cấu hình và giới hạn.
- **6:** kiểm tra tổng thể, checkout sạch, tài liệu và demo phản ánh đúng trạng thái thực tế.

## Quyết định cần chốt đúng thời điểm

| Thời điểm | Quyết định | Hướng đề xuất / điều còn thiếu |
| --- | --- | --- |
| Trước S1.1 | Nền code, môi trường và dependency | Giữ nền `94c5101`, không nhập nguyên nhánh remote. Dùng Python hiện có nếu dependency kiểm tra tương thích; tạo venv riêng, không sửa Python hệ thống. |
| S1.2 đã chốt | Phiên bản frontend và kết nối dev | Node 24.13.0/npm 11.6.2, React 19.3.1, TypeScript 7.0.2, Vite 8.3.4; lockfile và CLI/build đạt. Trang tĩnh chưa gọi API, chưa cần proxy/CORS. |
| Trước S2.1 | Loại biểu mẫu, trường và quy tắc | Đề xuất hóa đơn tổng hợp một trang, năm trường trong requirements; cần chốt required/null và quy tắc ngày/tiền. |
| Trước S3.2 | OCR engine/model | Tesseract là ứng viên có sẵn, cần đo trên mẫu; kiểm tra license, config, version và chất lượng dấu tiếng Việt. |
| Trước S3.3 | VLM local hoặc API | Chưa biết GPU/VRAM/ngân sách; khảo sát tài nguyên và model license. Nếu cần dịch vụ tính phí/gửi dữ liệu bên ngoài, trình phương án cụ thể để người dùng quyết định trước khi gọi. |
| Trước S4.1 | Giới hạn input và thời gian | Đề xuất PNG/JPEG một trang; chốt byte/pixel/timeout theo đo thực tế, chưa thêm PDF hoặc queue. |
| Trước S5.1–S5.2 | Dataset, chuẩn hóa và metric | Chốt mẫu khó, tách tập, ground truth, taxonomy và công thức trước khi chạy đánh giá để tránh chọn quy tắc theo kết quả. |

Không có quyết định provider nào chặn task health-check. Chưa cần database, Docker, cloud,
đa tài khoản hay nhiều loại biểu mẫu; bổ sung khi có nhu cầu và bằng chứng cụ thể.

## Definition of Done và báo cáo

Mỗi task cần đúng phạm vi, đọc/review diff, chạy kiểm tra phù hợp, cập nhật tài liệu cần thiết,
không có secret/cache/build/dữ liệu không được phép, stage đúng file, commit local thành công
và xác nhận branch/hash/status. Nếu chưa chạy được kiểm tra, ghi nguyên nhân và phạm vi chưa xác minh,
không đánh dấu đã kiểm thử. Nếu commit thất bại, báo lỗi thực tế và không bịa hash.

Báo cáo theo mẫu: **Task**, **Files changed**, **Implementation**, **Verification**,
**Git** (branch, hash, message), **Remaining issues**, **Next task**.
