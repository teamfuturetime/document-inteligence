# AI Usage Log - VT-042

Sinh viên: Phạm Nhật Quang, 23001920. Công cụ: OpenAI Codex; Git CLI, uv/pytest/ruff, coverage.py, Uvicorn/httpx2 và PDF tooling. Không ghi model ID khi không có thông tin xác nhận.

| Thời điểm | Prompt/tác vụ | Output sử dụng | Review và evidence |
| --- | --- | --- | --- |
| 30/10/2026 | Phân tích remote branches, thực hiện VT-042 trong bản sao, xuất PDF. | Thiết kế pairwise và thí nghiệm ban đầu. | Hai draft yếu W1/W2 được thay; log oracle số file sai được giữ trong bản evidence cũ. Không lấy bài VT-043. |
| 03/11/2026 | Người dùng: “git fetch origin --prune ... tất cả các remote branch ... tạo branch mới ... tự động push commit branch đó ... không trùng ... các thành viên”. | Audit 10 remote branches, nhánh riêng từ db727496. | Chỉ đối chiếu implementation của VT-043/VT-045, không sử dụng test/data/prompt/reflection của họ; `evidence/remote-audit.json`. |
| 03/11/2026 | Prompt P1 tại spec-and-plan.md: sinh test async/retry, real SQLite, Barrier, biên và red trước patch. | `backend/tests/test_async_retry_vt042.py`, 24 tests. | W1 thêm IDs/counts/files, W2 conflict bất biến. Thêm mất ACK sau commit, schema/origin conflict, preview write fault và provider unavailable. |
| 03/11/2026 | Thử baseline bằng suite VT-042 trước thay đổi implementation. | `evidence/red.log`. | Hai lỗi concurrency đúng nguyên nhân: 429 thay cho replay 202 hoặc conflict 409; các test còn lại pass. |
| 03/11/2026 | Sửa nhỏ sau red, kiểm tra diff và chạy lại suite. | 19 dòng trong service upload; `evidence/green.log`, `fix.patch`, `patch-review.json`. | Giữ UNIQUE và capacity; re-read key dưới BEGIN IMMEDIATE; thêm cleanup của request thua, không đổi expected để che lỗi. |
| 03/11/2026 | Đổi biên > thành >=, đo coverage và kiểm thứ tự/lặp tests. | `mutation.json`, `coverage.json`, `repeat.json`. | Boundary đúng B phát hiện mutant; API bytes được khôi phục. Runner thử đầu dùng node IDs theo backend rootdir nên exit 4; đã chuẩn hóa prefix và chạy lại 4 lượt thành công, giữ log thử đầu. |
| 03/11/2026 | Kiểm tải TCP150, native OCR, frontend và browser flow. | `performance.json`, `native-workflow.json`, `checks-*.json`, `browser-e2e.json`. | Tách p95 phản hồi khỏi OCR completion; giữ 429 trong mẫu; audit dependency được ghi riêng, không sửa lockfile ngoài slice. |
| 03/11/2026 | Chạy tải tuần tự sau checks, xuất bản nhánh và hoàn thiện PDF theo đề. | Nhánh GitHub thật, commit test/patch, renderer và PDF 8 trang chính + 3 phụ lục. | Lưu cả lượt đo cũ; đối chiếu metrics/commits, kiểm font Times New Roman, đen trắng, reflection 307 từ và nội dung không còn ghi thiếu nhánh/PR. |

Draft trước khi sửa (AI đã sinh, lưu để đối chiếu):

```python
# W1: status-only, không chứng minh retry giữ cùng record.
def test_retry_status_only(api):
    assert upload(api).status_code == 202


# W2: lặp happy path bằng key khác.
def test_upload_again(api):
    assert upload(api, key="OTHER").status_code == 202
```

W1 hiện kiểm hai lần gửi cùng key, so IDs, DB/event/revision count và source/preview files. W2 hiện gửi cùng key với payload khác, kiểm 409 và hash/run/files cũ không thay đổi. Đây là thay đổi oracle và phân bổ risk, không tăng số test lặp.

Hai giả định AI cần kiểm tra bằng code: (1) `async def` hoặc HTTP 202 không bảo đảm tác vụ đã tách khỏi request; (2) một tài liệu không nhất thiết tương ứng một file. Cả call path và storage layout đã được đối chiếu trước khi kết luận.
