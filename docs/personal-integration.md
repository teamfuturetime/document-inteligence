# Nhánh tích hợp cá nhân

`personal/canhtung-main` là nhánh tích hợp để bạn chạy thử công việc đang làm,
được tạo từ `chore/ci-checks` tại commit `55ae3c6`. Toàn bộ Phase 0–2 của chúng
ta đã là ancestor của commit này: không cần merge lại từng nhánh cũ.

Nhánh cá nhân này là ngoại lệ GitHub Flow theo yêu cầu của bạn. `main` chung
và PR #1 của thành viên khác được giữ nguyên. PR #1 dùng đơn đề nghị sinh viên,
chưa được tích hợp vào baseline hóa đơn; không có hai implementation chạy lẫn.

## Cách phát triển và thử nghiệm

1. Tạo feature branch từ `personal/canhtung-main`.
2. Chia atomic commits, chạy tests/schema/build cần thiết.
3. Merge feature đã kiểm tra vào nhánh cá nhân bằng merge thường, giữ lịch sử.
4. Chạy app theo [development.md](development.md). Chỉ những phase đã hoàn
   thành mới hoạt động; nhánh tích hợp không tự làm OCR/review/export hoàn chỉnh.
5. Khi đưa thay đổi vào repository chung, vẫn cần PR/reviewer/CI trước merge main.

```bash
git switch personal/canhtung-main
uv sync --locked
# Terminal 1:
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000
# Terminal 2, từ repository root:
cd frontend
npm ci
npm run dev
```

Hiện app có upload và fixed mock extraction. Xem [mock-demo.md](mock-demo.md)
để phân biệt mock với xử lý AI thật. Các module mới được ghi trạng thái rõ
trong [issues.md](issues.md).

Nhánh mới hiện local; push nhánh cá nhân cần được bạn cho phép. Nếu publish
trong repository chung, nhánh có cùng quyền truy cập với repository, không
phải repository riêng hoặc vùng dữ liệu riêng tư.

Không amend/rebase/reset/force push hoặc tự merge vào `main` chung. Notebook
ngoài repository và dữ liệu cá nhân thật không thuộc phạm vi tích hợp này.
