# Kiểm chứng bằng bản clone mới từ GitHub - 11/11/2026

Nhánh: https://github.com/teamfuturetime/document-inteligence/tree/bt3/23001945-vt044

README: https://github.com/teamfuturetime/document-inteligence/blob/bt3/23001945-vt044/individual/VT044/README.md

## Nguồn kiểm chứng

Clone mới trực tiếp từ remote, không dùng worktree cũ hoặc Git bundle local:

```bash
git clone --single-branch --branch bt3/23001945-vt044 https://github.com/teamfuturetime/document-inteligence.git bt3-review
cd bt3-review
```

HEAD tải về và thực sự được chạy: `dca06143f32434be5ab1c500975ff79dd6faf0a7`.
Bản cập nhật sau audit chỉ thay tài liệu/log, không đổi implementation/tests.

`git cat-file -e SHA^{commit}` và `git merge-base --is-ancestor SHA HEAD`
đã xác minh bốn commit dưới đây có mặt và thuộc lịch sử nhánh:

| Mốc | SHA |
|---|---|
| Baseline | `66074f4ecc384b6006ac8b574001a0b4aced86ef` |
| Behavioral RED | `911698f5b0a8e9942fb33f1bee7d480dae96b0c9` |
| Patch implementation | `72c9bcaf1713c230669c6d0aec7759ec90a48c55` |
| Test/evidence bổ sung | `286f659b68dc97bab14956aa33d53d7aa9b6092c` |

`evidence/remote-audit/inventory.json` ghi size/SHA-256 của 15 file bắt buộc
trong clone: README, plan, code, test, scripts, báo cáo và các log gốc.

## Chạy lại

Sau bước cài dependencies Python 3.12 trong README:

```bash
python -m pytest tests individual/VT044/test_lifecycle.py --cov=individual.VT044.harness --cov-branch --cov-report=term-missing
python -m individual.VT044.mutate
python -m individual.VT044.check_order
PYTHONPATH=backend:. python -m individual.VT044.load --transport asgi --output load-asgi-reproduced.json
PYTHONPATH=backend:. python -m individual.VT044.load --transport stdlib --output load-http-reproduced.json
git worktree add --detach ../bt3-red 911698f5b0a8e9942fb33f1bee7d480dae96b0c9
cd ../bt3-red
python -m pytest individual/VT044/test_lifecycle.py
```

Lệnh cuối phải exit 1 do các assertion RED chưa đạt; đó là kết quả mong đợi,
không phải lỗi cần sửa trong baseline. Script mutation thành công khi test bên
trong exit 1 và source nộp bài không bị đổi.

## Kết quả quan sát từ clone

| Kiểm chứng | Kết quả | Raw evidence trong `evidence/remote-audit/` |
|---|---|---|
| RED đúng commit | 21 failed, 7 passed, 1.13s | `red.log` |
| GREEN + regression | 133 passed, 6 warnings, 3.40s | `green.log` |
| Coverage harness | 93/93 dòng, 18/18 nhánh | `coverage.json` |
| Boolean mutation | Test T01-T03 phát hiện; source sạch giữ nguyên | `mutation.log` |
| Order | 34 instances x3 seeds đều pass | `order.log` |
| ASGI 200 tasks | 200/200, 1.200 responses hợp lệ, 0 lỗi; task p95 1.152119s | `load-asgi.json`, `.log` |
| HTTP 200 tasks | 195/200 thành công, 1.170 responses, 5 ConnectionResetError; task p95 1.012816s | `load-http.json`, `.log` |

ASGI đạt trong harness; HTTP chưa được nghiệm thu dù p95 dưới 5s. Không bỏ
HTTP errors hoặc diễn giải số đo ASGI thành production capacity.

## Quyền truy cập và giới hạn của audit

- `git ls-remote` và clone trong phiên này thành công, đúng ref/SHA nêu trên.
- GitHub connector và API không đăng nhập trả 404. Không khẳng định repository
  đọc được công khai hoặc người chấm đã được cấp quyền.
- Chủ repository cần bảo đảm người chấm có quyền đọc. Audit không đổi visibility,
  không thêm collaborator và không gửi tin nhắn mời ai.
- Đây là chạy lại từ remote trên cùng máy/interpreter local, không phải kết quả
  từ CI runner khác hoặc chứng nhận review độc lập bởi con người.
- Không có DOCX được cung cấp trong workspace; cập nhật báo cáo áp dụng cho bản
  Markdown và PDF hiện có, không khai nhận đã sửa file DOCX được nhắc tới.
