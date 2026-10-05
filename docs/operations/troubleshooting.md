# Xử lý lỗi

| Triệu chứng | Kiểm tra và cách xử lý |
| --- | --- |
| Fixtures503 / unconfigured | `.env` root hoặc DOCINTEL_PROVIDER_MODE=fixture explicit; restart; đây không engine failure cần mock fallback |
| Frontend không kết nối | Backend8000 đang chạy, proxy target/port đúng, /health và /capabilities; UI có retry |
| Port5173/8000 bận | Dừng đúng tiến trình mình mở hoặc chọn port có chủ ý và cập nhật proxy/CORS; không kill tiến trình người khác |
| Python/package mismatch | `.python-version`, `uv sync --project backend --locked`; không sửa expected tests để né bug |
| npm ci EPERM với native DLL | Dừng đúng Vite dev server của dự án trước npm ci/verifier; Windows khóa tệp native đang được dùng. Không dùng Administrator để né lỗi. |
| Node mismatch/npm ci fail | `.node-version` và engines, npm11.13.0; dùng lock hiện có, không bỏ lock để qua lỗi |
| Contract drift | Sinh backend contracts trước, frontend types sau; cập nhật examples/versions/tests, review semantic change |
| Ngày sai trong fixture005 | Cố ý: validation phải INVALID_DATE; không sửa nhãn để xanh |
| Thiếu glyph/tràn sau sinh dữ liệu | Font có dấu Việt và quyền dùng, --font rõ; đối chiếu cả ảnh/gold, cập nhật checksum/version |
| Console UnicodeEncodeError | Dữ liệu vẫn UTF-8; dùng Python -X utf8/PYTHONUTF8=1, diagnostic path không nên phá code |
| Docker không có | Báo blocked container execution; native checks vẫn chạy, không gọi là Docker passed |
| Provider thật chưa có | Capabilities ocr_ready false và benchmark not_measured; làm BL-002/003 thay vì trả prediction fixture giả |

Report lỗi bằng issue bug/data-model-error, ghi command/runtime/sample/run/config và dữ liệu được phép; không key/PII/full source không cần thiết.
