# Thực hiện/đối chiếu đúng thứ tự yêu cầu VT-044

Báo cáo được chia đúng **5 nhóm yêu cầu**, cùng thứ tự các gạch đầu dòng của
đề. Thứ tự trình bày này không thay ngày/thứ tự các thực nghiệm đã thực hiện;
baseline, RED, patch và các lần verify vẫn giữ đúng lịch sử Git và raw logs.

Mở Terminal ở root repository, dùng Python 3.12 và cài dependencies theo README.
Trên workspace hiện tại có thể dùng môi trường đã kiểm tra:

```bash
cd /Users/nguyencongtri/Documents/SE/bt3-vt044
source ../document-inteligence/.venv312/bin/activate
mkdir -p ../output/BT3_23001945_ordered
```

## 1. Specification và AI-assisted plan

1.1. Đọc problem statement, AC1-AC5 và NFC1-NFC4 ở mục 1.1 báo cáo.

1.2. Đọc invariant ở mục 1.2: owner isolation và bảo toàn dữ liệu liên quan.

1.3. Đối chiếu prompt, assumptions, plan và file dự kiến trong `PLAN.md`;
`PLAN_COMPLETION.md`, `LOAD_FIX_PLAN.md` là plan trước những đợt bổ sung tương ứng.

1.4. Đối chiếu source thật và hai phản biện: không có owner identity; retention
unlink tệp/cascade child. Phản hồi thật của sinh viên nằm ở
`evidence/student-review.md`, không khai lùi thời điểm phản hồi trước toàn bộ code.

## 2. Test strategy dựa trên risk

2.1. Đọc phân bổ unit, integration/API, E2E và test không cần trong báo cáo 2.1.

2.2. Đối chiếu bảng T01-T18 đủ sáu cột với `test_lifecycle.py`. Thu thập test
không sửa implementation:

```bash
python -m pytest --collect-only individual/VT044/test_lifecycle.py
```

Có 34 pytest instances, không phải 34 test-case logic: T01-T03 chung workflow,
nhiều cases được parametrize.

2.3. Đọc các cạnh active/deleted, self-loop và boundary data ở mục 2.3.

2.4. Kiểm tra negative T05/T06/T07/T13 và failure-path T11 gắn R1/R3.

## 3. Test-first AI-assisted implementation

3.1. Xác định slice: owner-scoped delete/restore, read/list/content/extraction
trong harness với ORM/repository/storage thật.

3.2. Nhánh cá nhân `bt3/23001945-vt044`; baseline:
`66074f4ecc384b6006ac8b574001a0b4aced86ef`. Không merge trước team review.

3.3. Tái hiện behavioral RED trong worktree riêng; giữ nguyên nhánh hoàn thiện:

```bash
VT044_REVIEW_ROOT="$(pwd)"
git worktree add --detach ../bt3-red-ordered 911698f5b0a8e9942fb33f1bee7d480dae96b0c9
cd ../bt3-red-ordered
python -m pytest individual/VT044/test_lifecycle.py
cd "$VT044_REVIEW_ROOT"
```

Dùng tên thư mục worktree mới nếu `../bt3-red-ordered` đã tồn tại.
RED kỳ vọng **21 failed, 7 passed**, pytest exit 1; nguyên nhân là scaffold 501.
`setup-missing-module.log` là lỗi setup khác và không được dùng thay RED.

3.4. Review patch chuyển trạng thái của C_IMPL:

```bash
git show 72c9bcaf1713c230669c6d0aec7759ec90a48c55 -- individual/VT044/harness.py
```

Đối chiếu `evidence/review.md`: owner predicate, locks, expiry/processing guards,
chỉ đổi tombstone, commit/rollback và response trung tính. Sinh viên đã xác
nhận tự review; chưa khai nhận team review.

3.5. Chạy GREEN và regression trên nhánh hoàn thiện:

```bash
python -m pytest individual/VT044/test_lifecycle.py
python -m pytest tests individual/VT044/test_lifecycle.py
```

Kỳ vọng lần lượt **34 passed** và **133 passed**. Log gốc ở `evidence/`, log
clone trực tiếp GitHub ở `evidence/remote-audit/`.

3.6. Đọc lý do dùng ngoại lệ harness và giới hạn tại `REVIEW_GUIDE.md`; không
tuyên bố các route production đã có per-user authorization.

## 4. Đánh giá chất lượng test - “Who tests the tests?”

4.1-4.2. Tạo mutant trong Git branch tạm và chứng minh test bắt lỗi:

```bash
python -m individual.VT044.mutate
```

Kỳ vọng `mutant_killed=True`, `submission_source_unchanged=True`. Dòng FAILED
trong pytest con là mong đợi. Mutant `!= -> ==` không nằm trong nhánh nộp.

4.3. Chạy coverage, đọc cả line/branch và risk coverage:

```bash
python -m pytest individual/VT044/test_lifecycle.py --cov=individual.VT044.harness --cov-branch --cov-report=term-missing --cov-report=json:../output/BT3_23001945_ordered/coverage.json
```

Harness đã đạt 93/93 lines, 18/18 branches; không suy diễn thành toàn hệ thống.

4.4. Kiểm tra time boundary, order/shared state và contention cùng Document:

```bash
python -m individual.VT044.check_order
```

Ba seeds 44, 1945, 23001945 x34 instances đều đã qua; time được inject trong
fixtures, T15 dùng barrier/session độc lập. Không thêm timed sleep để che flaky.

4.5. Chạy tải 200 tác vụ, giữ riêng từng profile:

```bash
PYTHONPATH=backend:. python -m individual.VT044.load --transport asgi --output ../output/BT3_23001945_ordered/load-asgi.json
PYTHONPATH=backend:. python -m individual.VT044.load --transport stdlib --connection-mode cold --output ../output/BT3_23001945_ordered/load-cold.json
PYTHONPATH=backend:. python -m individual.VT044.load --transport stdlib --connection-mode preconnected --output ../output/BT3_23001945_ordered/load-preconnected.json
```

Cold còn lỗi và có thể exit 1; giữ dữ liệu đó thay vì retry/chọn bỏ lượt lỗi.
Preconnected có 200 setup GET ngoài pha đo, rồi 200 tác vụ đồng thời với 1.200
request đo; tổng 1.400 request. Setup không tính vào p95, được ghi riêng.
ASGI bỏ qua socket. Chỉ kết luận trong đúng profile đã đo; không nói production
đạt từ một trong các profile này. Đọc `HTTP_LOAD_NOTES.md` trước diễn giải số liệu.

## 5. Engineering evidence và reflection

5.1. Đọc traceability ở báo cáo 5.1: AC/Risk -> case -> file -> commit -> result.

5.2. Đối chiếu AI Usage Log ở Phụ lục A với plan, output được dùng, sửa/bác bỏ
và raw evidence; gồm cả đợt chẩn đoán HTTP ngày 12/11.

5.3. Giải thích hai điểm AI chưa đáng tin ngay: shared key không đồng nghĩa
owner authorization; response echo target không chứng minh state đã persist.

5.4. Đọc reflection 324 từ; giữ đúng confidence, residual risks và next test.

## Đầu ra và nộp bài

PDF `BT3_23001945_VT-044.pdf`: tối đa 8 trang nội dung chính, appendices không
tính giới hạn. Nộp kèm link branch chứa test/patch/README trên Google Classroom.
URL nhánh: https://github.com/teamfuturetime/document-inteligence/tree/bt3/23001945-vt044

Chưa xác nhận người chấm có quyền đọc repo (ẩn danh từng trả 404); chủ repo cần
bảo đảm quyền. Không gửi email, không merge trước nhóm review, không khai nhận
đã nộp Classroom. Đề không bắt buộc tạo PR nếu đã có branch link hợp lệ.
