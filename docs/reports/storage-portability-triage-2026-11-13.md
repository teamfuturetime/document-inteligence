# Triage storage nguồn Minh Thảo — issue #11

Nguồn `minhthao@760ccdc`, `backend/app/services/storage.py` và `tests/unit/test_storage.py`. Test kỳ vọng `StorageSecurityError` cho key Windows `C:\temp\file`, kể cả khi chạy POSIX. `_resolve` dùng `Path.is_absolute()` và `Path.name`, vốn theo platform host; trên POSIX dấu backslash không phân cách thư mục và drive letter không làm đường dẫn absolute. Vì thế key đó đi qua validation, sau đó `read_bytes()` gặp FileNotFoundError thay vì lỗi security được test kỳ vọng.

Đã tái hiện riêng phần Path semantics bằng Python thật trên macOS; không tuyên bố chạy full source backend/PostgreSQL test suite. Có thể lặp lại:

```python
from pathlib import Path, PureWindowsPath
key = r"C:\temp\file"
assert not Path(key).is_absolute()  # POSIX
assert Path(key).name == key
assert PureWindowsPath(key).is_absolute()
```

Ngoài ra source resolve symlink trước khi kiểm `.is_symlink()`, nên không thể chỉ dựa vào lần kiểm sau resolve để phát hiện symlink nội bộ. Không port nguyên storage source trước khi xử lý ranh giới cross-platform/symlink.

Quyết định: giữ LocalDocumentStorage của docintel, chỉ nhận document ID lowercase hex do server sinh và kind source/preview; không dùng tên file client làm storage key. Bổ sung tests Windows/POSIX paths và symlink ở mốc storage của task này. Không sửa submission branch/report hoặc nhận source auth/storage là code production đã port. Nếu cần sửa nhánh nguồn riêng, dùng issue/PR có kiểm chứng source dependencies; task hiện tại chỉ triage và harden storage được chọn.
