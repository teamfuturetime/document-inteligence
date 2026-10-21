# Roadmap phát triển cá nhân

## Cách thực hiện

Giai đoạn 0 và S1.1 đã hoàn thành; S1.2 có kiểm tra CLI/HTTP/render nhưng còn thiếu
kiểm tra trực quan frontend. S3.2 thêm OCR adapter/CLI, mẫu tổng hợp và test,
giữ điểm còn mở này và không tuyên bố toàn bộ Giai đoạn 1 đã kiểm thử đầy đủ.
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
| S2.1 — Chốt hóa đơn và schema (tài liệu) | `docs/requirements.md`, `docs/architecture.md`, `docs/roadmap.md`, README | Chốt hóa đơn bán hàng tổng hợp một trang, năm trường và schema 1.0.0; nêu normalization, confidence, ranh giới dữ liệu, giả định và giới hạn. | Rà soát nhất quán đặc tả, JSON minh họa hợp lệ, liên kết nội bộ, diff; commit tài liệu. Chưa có schema/validation thực thi. | Đã kiểm thử (tài liệu) |
| S2.1a — Model canonical và unit test offline | `backend/app/schemas/__init__.py`, `backend/app/schemas/invoice.py`, `backend/tests/test_schemas.py`, tài liệu liên quan | Hai model canonical dùng Pydantic có sẵn; không normalize input thô, không thêm API/envelope AI. | Kiểm tra required/null, strict types, extra key/metadata, số 0 đầu, ngày thật, giới hạn tiền/chuỗi, NFC/khoảng trắng/control, JSON round-trip và gán lại giá trị; 207 test schema + 2 health test đạt. | Đã kiểm thử |
| S2.2 — Normalization và business validation | `backend/app/services/`, `backend/app/schemas/validation.py`, `backend/tests/test_{normalization,validation}.py`, tài liệu liên quan | Tách chuyển đổi raw thành candidates khỏi validation bằng model có sẵn; snapshot nguồn, locale/version, lỗi theo trường có namespace. | 161 test mới cho format/Unicode/required/types/range/ambiguity/currency/multiple errors/immutability và result consistency; toàn bộ 370 backend tests đạt, model/health/frontend giữ nguyên. | Đã kiểm thử (service local; chưa có API) |
| S3.1 — Pipeline contract và fake | `backend/app/providers/`, `backend/app/schemas/extraction.py`, `backend/app/services/pipeline.py`, `backend/tests/test_pipeline.py`, tài liệu | Protocol nhận ID/MIME/bytes; raw candidates/metadata riêng, dùng lại S2.2; fake tổng hợp có nhãn/version. | 49 test mới, toàn bộ 419 backend tests đạt: success khác valid, missing/uncertain, metadata, deterministic, sai output, lỗi và timeout giả lập; không dependency mới. Chưa giải mã ảnh/deadline thực. | Đã kiểm thử (offline; chưa OCR/VLM thật) |
| S3.2 — OCR thật trên ảnh mẫu | `schemas/ocr.py`, `providers/{ocr,tesseract}.py`, `ocr_cli.py`, `data/ocr-smoke/`, tests OCR, dependency/config và tài liệu | OCRProvider riêng, Tesseract/vie thật, Pillow decode/EXIF; giữ raw text/TSV/native score và version/hash; không đổi S3.1/canonical schema. | Toàn bộ 463 tests đạt, gồm 37 unit OCR và 7 integration/mẫu; bắt buộc engine thật cũng đạt. PNG/JPEG, Unicode, blank/corrupt, EXIF, guards, cleanup và timeout subprocess; giới hạn chất lượng ở docs/ocr.md. | Đã kiểm thử local (chưa extraction/VLM/API/UI) |
| S3.3 — VLM thật và confidence | Extraction adapter, tests extraction, cấu hình prompt/model, tài liệu provider | Chọn model theo môi trường/quyền dùng/chi phí; ảnh + OCR + schema → fields; kiểm tra output, ghi provenance và chính sách confidence. | Ví dụ inference thật từ ảnh mẫu; test fake cho JSON lỗi, thiếu trường, timeout; confidence null nếu chưa có cơ sở; model/prompt/config version đầy đủ. | Đã khảo sát bước S3.3.1; chưa triển khai VLM/inference hoặc tích hợp |
| S3.3.1 — Khảo sát VLM | `docs/vlm-survey.md`, README, roadmap | Xác minh Git/phần cứng, model card/license/giá; shortlist Qwen, InternVL, Gemini; đề xuất benchmark và confidence/provenance. | Bảng nguồn chính thức, phân biệt thông tin xác minh/ước tính/chưa đo, nhãn/schema/hash hợp lệ; review tài liệu/diff. Không tải/chạy model. | Đã khảo sát và kiểm tra tài liệu |
| S3.3.2 — Runner benchmark local và parser/evidence adapter | Tách thành a/b theo prompt hiện tại | a xây nền offline; b mới tải/chạy model sau khi được cho phép. | Không coi fixture test là inference/model benchmark. | Đã có nền offline a; b chưa triển khai |
| S3.3.2a — Runner/parser/evidence offline | `backend/app/benchmark/`, `backend/tests/test_benchmark.py`, `data/benchmark-fixture/`, tài liệu | Ba mode, strict JSON/fence parser, nguồn text span/bbox, labels riêng, typed/normalized/null/error metrics, report fixture có version/hash. | 68 test mới, toàn bộ 531 tests đạt; giữ S3.1/S3.2/schema, confidence null; không VLM/API/dependency mới. | Đã kiểm thử offline |
| S3.3.2b — Inference thật và benchmark | `docs/vlm-preflight.md`; sau phê duyệt mới thêm runtime/model adapter, OCR snapshots/provenance, runner guard và report thật | Preflight đã xác minh revision/checksum công bố và nguồn runtime CPU; tải/chạy chỉ sau xác nhận của người dùng. | Ít nhất một inference ảnh và report 9 run ban đầu hoặc lỗi thực tế; quality/time/memory thật, nguồn evidence kiểm chứng, unit/full tests. | Chỉ có preflight Giai đoạn 0–1; chưa tải model/runtime hoặc chạy inference |
| S4.1 — Upload tới pipeline | Backend route và file validation, `frontend/src/` upload/API client, tests | PNG/JPEG một trang, giới hạn byte/pixel, kiểm tra nội dung, file tạm, trạng thái chờ/lỗi. | API test file sai loại/quá lớn/hỏng, test chọn/gửi file và UI lỗi; chứng minh pipeline nhận đúng ảnh; dọn file tạm. | Chưa triển khai |
| S4.2 — Review/edit từng trường | Frontend review/preview, type contract và tests | Giữ extraction gốc, bản sửa độc lập; hiển thị evidence/confidence có nguồn và cảnh báo. | Test sửa từng trường, giữ giá trị gốc, trường null, nhập chưa hợp lệ, reset xác nhận sau sửa; contract khớp backend. | Chưa triển khai |
| S4.3 — Validate bản review | Backend validation API, frontend validation flow, API/UI tests | Dùng lại service S2.2; hiện lỗi theo trường, chỉ xác nhận payload đang hợp lệ. | Test lỗi backend hiện đúng; sửa sau validation vô hiệu hóa xác nhận cũ; không bỏ qua validation backend. | Chưa triển khai |
| S4.4 — Export JSON và demo luồng chính | Backend export route/service, frontend download, tests và hướng dẫn demo | Validate lại payload cuối, yêu cầu xác nhận, xuất dữ liệu sửa kèm provenance và version. | Test từ chối chưa hợp lệ/chưa xác nhận, lỗi tạo/tải file, JSON đúng Unicode/giá trị sửa; E2E upload → review → validate → export với fake. | Chưa triển khai |
| S5.1 — Golden dataset | `data/golden/`, manifest, hướng dẫn annotation và kiểm tra data | Bộ nhỏ tổng hợp có ground truth; nguồn/quyền dùng/hash/version, tách tuning/evaluation. | Kiểm tra schema/hash/ID; rà soát ảnh so với ground truth; có biến thể khó và trường thiếu, không lộ gold vào provider. | Chưa triển khai |
| S5.2 — Metrics, taxonomy và báo cáo | `evaluation/`, tests metrics/report, `docs/evaluation.md` | Field exact match và PRF theo định nghĩa yêu cầu; phân loại lỗi; report gắn dataset/model/config/code version. | Test phép tính bằng ví dụ tính tay, null/null, mẫu số 0; CLI tạo report chạy lại được; tách fake baseline với kết quả AI thật. | Chưa triển khai |
| S6.1 — Kiểm chứng và demo | Tests luồng chính/biên, README, `docs/testing.md`, demo và báo cáo giới hạn | Chạy kiểm tra tổng thể, thử bản checkout sạch với dependency đã khóa; demo fake và real phân biệt rõ. | Backend/frontend tests, build và E2E đạt; chạy theo README ở checkout sạch; evaluation có báo cáo; cập nhật trạng thái dựa trên bằng chứng. | Chưa triển khai |

S1.1 dùng commit message `feat: add backend health check`.
S1.2 dùng commit message `feat: initialize React frontend`.
S2.1 dùng commit message `docs: define MVP invoice data contract`.
S2.1a dùng commit message `feat: add canonical invoice value models`.
S2.2 dùng commit message `feat: add invoice normalization and business validation`.
S3.1 dùng commit message `feat: define extraction pipeline contract`.
S3.2 dùng commit message `feat: add local Tesseract OCR adapter`.
Task tiếp theo duy nhất là **S3.3.2b — Runtime/model và benchmark inference thật**,
theo [benchmark offline](benchmark-offline.md), sau khi phạm vi/runtime/model download được cho phép.
S3.3.1 là khảo sát, S3.3.2a chỉ fixture; chưa có benchmark VLM hoặc tích hợp provider thật.
S2.2 đã được gọi từ pipeline local, chưa tích hợp vào API/AI thật hoặc UI.
Tách S2.1a khỏi S2.1 theo yêu cầu hiện tại để review quyết định dữ liệu trước khi code;
không đưa normalization, API hoặc toàn bộ validation pipeline vào một task.
Kiểm tra trực quan frontend vẫn còn mở, không xem typecheck/build là thay thế việc đó.
Các commit sau đặt theo phạm vi thực tế, không theo số lượng task. Nếu một task lớn hơn dự kiến,
tách phần độc lập kiểm tra được và cập nhật roadmap trước khi mở rộng.

## Điều kiện hoàn thành từng giai đoạn

- **0:** khảo sát, tài liệu được kiểm tra và commit; không tạo ứng dụng.
- **1:** backend/frontend chạy theo hướng dẫn, health-check HTTP hoạt động, test cơ bản và build đạt.
- **2:** S2.1 chốt tài liệu; S2.1a/S2.2 hiện thực schema/business validation có test
  tự động, không phụ thuộc AI. Tài liệu S2.1 không đủ để đánh dấu giai đoạn hoàn thành.
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
| S2.1 đã chốt, S2.1a/S2.2 đã kiểm thử local | Loại biểu mẫu, trường và quy tắc | `sales_invoice` 1.0.0 không đổi; hai model, normalization nguồn vi-VN và business validation đã có test. Locale phải do bên gọi xác định; chưa có chọn candidate AI, validation API hoặc review. |
| S3.2 đã chốt cho smoke local | OCR engine/model | Tesseract 5.5.0 + vie tessdata_fast, OEM 1/PSM 6/DPI 300; license/hash/config, so sánh vie/vie+eng và lỗi dấu ở docs/ocr.md và ADR 0001. Chưa benchmark nhiều engine hoặc golden dataset. |
| S3.3.1 đã khảo sát, chưa chốt provider | VLM local hoặc API | Core Ultra 5 125H, khoảng 31.5 GiB RAM, CIM thấy Intel Arc; dedicated VRAM/backend tăng tốc chưa xác định. Đề xuất Qwen GGUF CPU có điều kiện; API cần chốt quyền gửi dữ liệu/ngân sách trước khi dùng. Chi tiết nguồn/giới hạn ở docs/vlm-survey.md. |
| Trước S4.1 | Giới hạn input và thời gian | Đề xuất PNG/JPEG một trang; chốt byte/pixel/timeout theo đo thực tế, chưa thêm PDF hoặc queue. |
| Trước S5.1–S5.2 | Dataset, chuẩn hóa và metric | Chốt mẫu khó, tách tập, ground truth, taxonomy và công thức trước khi chạy đánh giá để tránh chọn quy tắc theo kết quả. |

Không có quyết định provider nào chặn task health-check. Chưa cần database, Docker, cloud,
đa tài khoản hay nhiều loại biểu mẫu; bổ sung khi có nhu cầu và bằng chứng cụ thể.

## Definition of Done và báo cáo

Mỗi task cần đúng phạm vi, đọc/review diff, chạy kiểm tra phù hợp, cập nhật tài liệu cần thiết,
không có secret/cache/build/dữ liệu không được phép, stage đúng file, commit local thành công
và xác nhận branch/hash/status. Nếu chưa chạy được kiểm tra, ghi nguyên nhân và phạm vi chưa xác minh,
không đánh dấu đã kiểm thử. Nếu commit thất bại, báo lỗi thực tế và không bịa hash.
S3.3.1 và S3.3.2a đã được giữ chưa commit theo yêu cầu khi triển khai. Phiên finalize
22/10/2026 cho phép commit/push toàn bộ tiến trình hợp lệ sau kiểm tra; kết quả thực tế
ghi trong [bàn giao phiên](session-handoff.md). Việc này không cấp phép tải model/runtime
hoặc đánh dấu S3.3.2b hoàn thành.

Báo cáo theo mẫu: **Task**, **Files changed**, **Implementation**, **Verification**,
**Git** (branch, hash, message), **Remaining issues**, **Next task**.
