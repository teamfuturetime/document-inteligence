# Khảo sát repository — Giai đoạn 0

## Phạm vi và bằng chứng

Khảo sát ngày **20/10/2026**, dựa trên working tree và remote-tracking refs có sẵn
trong local. Không fetch, không xác minh trạng thái mới nhất trên GitHub,
không checkout hoặc chạy code của các nhánh tham khảo.

Trước thay đổi:

- Branch: `tuannguyen`.
- `git status --short --branch`: chỉ có `## tuannguyen`, working tree sạch.
- HEAD: `94c5101` — `first commit`, ngày commit `2026-10-05T16:30:17+07:00`.
- `git ls-files`: chỉ có `README.md`, nội dung ban đầu là `# document-inteligence`.
- Không tìm thấy `AGENTS.md` trong working tree hoặc các thư mục cha đã kiểm tra.
- Có bốn nhánh local: `congtri`, `main`, `minhthao`, `tuannguyen`, cùng tại `94c5101`.
- Có bảy nhánh remote-tracking thực; `origin/HEAD` là con trỏ tới `origin/main`,
  không tính thành một nhánh bổ sung.

## Các nhánh đã khảo sát

Danh sách file và ba commit gần nhất của mỗi nhánh được đọc bằng Git.
Các nhận xét code dưới đây chỉ áp dụng cho phần đã đọc, không phải chứng nhận
toàn bộ tính năng trên nhánh đó đã hoàn thành.

| Remote-tracking ref | Commit | Kết quả quan sát và nguồn code tiêu biểu |
| --- | --- | --- |
| `origin/main` | `94c5101` | Cùng commit nền với nhánh hiện tại; chỉ có README. |
| `origin/feat/backend-skeleton` | `a281029` | `backend/src/document_backend/main.py` tạo FastAPI app, đăng ký health router và error handlers. Cây file có schema, fixtures và test. |
| `origin/chore/ci-checks` | `55ae3c6` | Có backend, frontend, CI và mẫu tổng hợp. `backend/src/document_backend/services/mock_extraction.py` trả giá trị cố định, không đọc nội dung upload và để confidence null. |
| `origin/personal/canhtung-main` | `61a31ab` | `pipeline/src/document_pipeline/ocr.py` dùng Tesseract; `extraction.py` khớp nhãn và luật, không phải VLM trong phần đã đọc. `schemas/src/document_contracts/models.py` tách OCR/extraction/validation/export; `evaluation/src/document_evaluation/metrics.py` tính exact match và PRF. Cây file có review UI, golden data và test. |
| `origin/congtri` | `99471ef` | `backend/app/main.py` khởi tạo database, CORS và API tài liệu; `ai_service/ocr/engines.py` có PaddleOCR adapter và empty fallback. Cây file có React UI, migration, Docker và test. |
| `origin/minhthao` | `da108de` | `ai_service/classification/engine.py` phân loại bằng keyword/regex, confidence dựa trên tỉ lệ điểm. Cây file có OCR, extraction, database và test. Không đồng nhất confidence phân loại với confidence từng trường. |
| `origin/nhatquang` | `f37bfbd` | `backend/src/docintel/adapters/fixture.py` đọc OCR/prediction fixture theo ID. `api/app.py` công bố OCR, extraction, upload, review và export là planned; các fixture endpoint chỉ là nền tảng minh họa. |

Code tham khảo chưa được chạy test trong lần khảo sát này. Không sử dụng tên commit
hoặc số lượng file làm bằng chứng tính năng hoạt động; không đánh dấu yêu cầu
trên `tuannguyen` hoàn thành nhờ code tồn tại trên nhánh khác.

## Môi trường local

| Công cụ | Kết quả thực tế | Giới hạn kiểm tra |
| --- | --- | --- |
| Python | `3.13.7` | Chỉ chạy `python --version`; chưa tạo venv/cài package. |
| Node.js | `v24.13.0` | Chỉ chạy `node --version`; chưa build frontend. |
| npm | `11.6.2` | Chỉ chạy `npm --version`; chưa cài dependency. |
| Git | `2.52.0.windows.1` | Đã đọc branch, status, lịch sử và tree. |
| uv | Không tìm thấy qua `Get-Command` | Không bắt buộc thêm; có thể bắt đầu bằng venv/pip. |
| Tesseract | `5.5.0.20241111` | `--list-langs` thấy `eng`, `osd`, `script\Vietnamese`, `vie`; chưa nhận dạng tài liệu. |

Chưa khảo sát GPU/VRAM, chưa tải weights, chưa kiểm tra API key, giấy phép model,
chi phí provider hoặc chất lượng OCR tiếng Việt. Các mục này là đầu vào của task
chọn provider; chưa cần chúng để viết health-check.

## Kết luận cho nhánh cá nhân

Giữ nền hiện tại và phát triển từng task nhỏ trên `tuannguyen`. Các nhánh tham khảo
có phạm vi và cấu trúc khác nhau; không merge một ứng dụng lớn vào giai đoạn khảo sát.
Có thể học cách tách contract, fake provider và evaluation; nếu tái sử dụng code sau
này cần đọc phần liên quan, kiểm tra dependency/giấy phép và xác minh bằng test riêng.

Kiến trúc dự kiến ở [architecture.md](architecture.md); các quyết định còn mở
và task tiếp theo ở [roadmap.md](roadmap.md).

## Các lệnh khảo sát chính

```powershell
git branch --show-current
git status --short --branch
git log -5 --oneline --decorate
git for-each-ref --format="%(refname:short)|%(objectname:short)|%(symref)" refs/heads refs/remotes
git ls-files
rg --files -g AGENTS.md -g '!node_modules' -g '!.git'
git ls-tree -r --name-only origin/personal/canhtung-main
git show origin/feat/backend-skeleton:backend/src/document_backend/main.py
python --version
node --version
npm --version
git --version
tesseract --version
tesseract --list-langs
```

`rg` không tìm thấy file phù hợp có thể trả exit code 1; đây không phải lỗi ứng dụng.
Ngoài ví dụ trên, `git ls-tree`, `git log` và `git show` đã được dùng trên các ref
và file tiêu biểu trong bảng khảo sát. Chưa chạy pytest, frontend test, lint, build
hoặc evaluation vì nhánh hiện tại chưa có những thành phần đó.

## Kiểm tra tài liệu Giai đoạn 0

Đã chạy kiểm tra bằng Python inline trên năm file Markdown: đọc UTF-8 thành công,
sáu liên kết nội bộ trỏ tới file tồn tại trong repo, đủ và đúng thứ tự R01–R12,
đủ 15 task trong roadmap, không có trailing whitespace hoặc conflict marker.
`git diff --check` đạt; nội dung đã được đọc và đối chiếu với kết quả khảo sát.
Đây là kiểm tra tài liệu, không phải test ứng dụng hay đánh giá chất lượng AI.
