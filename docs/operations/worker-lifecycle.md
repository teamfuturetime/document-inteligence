# Process crash/restart và runtime locks — issue #47

Product app/worker dùng RuntimeLock thật; không chạy hai app/worker cho cùng runtime. Sau crash,
OS giải phóng lock, file lock có thể còn tồn tại. Không xóa file lock để ép chạy process thứ hai.
Startup worker sau khi lấy lock mới recover các runs running thành failed/PROCESSING_INTERRUPTED;
queued giữ khả năng xử lý tiếp, không tự xác nhận tài liệu hoặc tạo thành công giả.

## Kiểm chứng bằng process thật

```sh
uv run --project backend --locked pytest backend/tests/test_worker_process.py -q
uv run --project backend --locked python scripts/check_worker_lifecycle.py
```

Lệnh pytest chạy mười cases qua subprocess Uvicorn/HTTP loopback/SQLite/files thật, **fixture
inference double tường minh**. Không đo OCR accuracy. Lệnh script chạy **native Tesseract/models
thật**, upload ảnh synthetic, xử lý thành công rồi graceful stop/restart và đối chiếu persisted
detail; thiếu engine/models phải fail, không fallback. Chỉ dùng runtime mới trong thư mục tạm.
App không có debug/control endpoint mới. Child harness riêng dùng stdin/stdout pipe handshakes;
không seed accounts hoặc đổi app mặc định. Native smoke không đọc annotations/gold.

Các cases kiểm:

- Kill khi queued/running trong local và session; app process/worker process thứ hai bị chặn,
  không recover job của process đang sống. Restart sau khi OS release lock mới recover running.
- Session alpha/beta giữ owner isolation sau restart; interrupted không có review/confirm giả.
- Completed/confirmed source/detail/history và JSON export giữ nguyên sau crash một job khác,
  ở cả local/session. So sánh history trước GET export mới vì export tạo audit event hợp lệ;
  exported_at sinh mới không dùng để kết luận persisted content đổi.
- Graceful inference giữ gate qua handshake worker_closing; bounded event wait0.5s xác nhận
  worker close chưa hoàn tất trước release, sau đó chờ cycle_finished/worker_closed và persisted
  succeeded. Cùng oracle phải từ chối child-only mutant bỏ join/lock release; mutation chỉ
  được bật trong fixture mode với temp-runtime marker, không áp dụng cho app/native mặc định.
- Child lỗi có exit code/handshake và stderr tail tối đa40dòng, mỗi dòng512ký tự;
  parent đọc stderr riêng để không chặn child vì pipe đầy.

Harness không sleep đoán thời điểm: upload202, inference-start/cycle-finished, hold và shutdown
có handshake; mọi wait/request/process cleanup có deadline. Parent kill trên POSIX là SIGKILL,
Windows dùng TerminateProcess; graceful POSIX dùng SIGTERM, Windows dùng pipe yêu cầu Uvicorn
shutdown (không claim đã kiểm Windows console Ctrl-C/SIGTERM). Uvicorn có thể re-raise SIGTERM
sau cleanup nên exit -SIGTERM được nhận **chỉ sau lifespan_stopped handshake**; kill -SIGKILL
không được coi là graceful. Child độc lập không nhận runtime thiếu marker của harness.

Runtime temp/session accounts synthetic được parent tạo rõ ràng, không đưa passwords/cookies,
DB/images/traces lên GitHub. Parent đóng/kills child theo deadline khi lỗi; fixture crash không
chạy native grandchild. Native smoke chỉ shutdown sau inference hoàn tất, không claim power-loss,
disk crash consistency hoặc quản lý native descendants khi OS kill cưỡng bức.

Git provenance rev-parse/status là noninteractive, dùng stdin DEVNULL để không cạnh tranh với
control reader của harness. Regression riêng ở pipeline/tests/test_provenance.py kiểm cả hai
commands và chạy Git thật trong child đang giữ control pipe; Windows job chạy cùng regression.
Đây là kiểm đường metadata của native pipeline, không tự nhận native OCR Windows đã chạy.

CI backend chạy các cases trên Ubuntu; Windows job hiện có thêm cùng suite và Git pipe tests. OCR integration
giữ native local/session rồi chạy native process smoke; gate sáu product jobs + Product checks
giữ nguyên. Kết quả thực tế cần gắn đúng head, không suy Windows đã PASS từ macOS.
