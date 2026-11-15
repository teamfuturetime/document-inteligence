# Nghiệm thu tích hợp OCR hóa đơn

Task điều phối [#21](https://github.com/teamfuturetime/document-inteligence/issues/21), kế hoạch nhóm [#15](https://github.com/teamfuturetime/document-inteligence/issues/15). Đây là checklist kỹ thuật, không phải bảng chấm điểm hoặc xác nhận thành viên đã nghiệm thu. Tùng điều phối; chủ tính năng tự kiểm thử; Tuấn phụ trách review dữ liệu/QA theo phân công. Kết quả phải gắn với source SHA thực tế.

## Chuẩn bị một lần nghiệm thu

1. Dùng main đã cập nhật hoặc SHA ứng viên được ghi rõ, đọc [README](../../README.md), [contract](../../contracts/README.md) và [runbook](../product/runbook.md). Không dùng working tree của nhánh cá nhân cũ làm bằng chứng cho main. Ghi `git rev-parse HEAD` và `git status --short`; không gọi checkout bẩn là sạch.
2. Cài dependencies theo lock, đúng runtime pins. Chạy model helper để kiểm hai weights vie/eng đã pin; ghi engine, config/source hashes từ report native. Thiếu engine/model phải fail, không bật fixture để thay OCR thật.
3. Chỉ dùng synthetic/sample có quyền. Dùng DB/runtime tạm riêng cho nghiệm thu; không đưa source files, DB, models, logs hoặc bản export người dùng vào Git. Các helpers verify_product/check_upload_ingress tự tạo runtime tạm.
4. Phân biệt **có test** với **đã chạy đạt**, **mock pipeline** với **native OCR**, **workflow scripted review** với **accuracy máy trước review**. Các ca chưa chạy ghi Pending hoặc Blocked kèm dependency; không điền Pass vì CI của PR khác xanh.

## Ma trận cho main hiện có

Nền tham chiếu `921541d` đã có upload budgets qua PR #16. Các đường dẫn dưới là coverage có sẵn, chưa tự chứng minh lần chạy mới đã đạt. Khi thay source, chạy kiểm tra phù hợp và ghi kết quả lại.

[Baseline ngày 14/11/2026](../reports/integration-baseline-2026-11-14.md) ghi kết quả đã chạy trên cùng source sản phẩm, phân biệt 131 tests, native workflow và HTTP ingress với browser/feature còn Pending.

| Ca | Thao tác/điều kiện | Kết quả mong đợi | Coverage hiện có |
|---|---|---|---|
| U1 — giới hạn và body hỏng | Content-Length quá lớn/lặp/sai, stream vượt cap, mismatch, disconnect | 400/413 đúng envelope; không document/run/event/source/preview mới; slot được giải phóng | [ASGI ingress tests](../../backend/tests/test_upload_ingress.py), [receiver tests](../../backend/tests/test_upload_receiver.py) |
| U2 — timeout/admission | Hai upload nhỏ giọt; request thứ ba; hủy khi nhận và khi persistence đang chạy | Tổng receive deadline không reset theo chunk; busy 429 không đợi; slot giữ đến lúc thread lưu kết thúc, sau đó dùng lại được | Ingress tests ở trên; [probe HTTP loopback](../../scripts/check_upload_ingress.py) |
| U3 — retry sau mất response | Cùng key + ảnh/type/origin sau khi upload đã commit; thử nội dung khác cùng key | Cùng document/run, không nhân file/record; nội dung khác 409, kể cả queue đầy | [retry regression](../../backend/tests/test_async_retry_vt042.py), [product tests](../../backend/tests/test_product.py) |
| O1 — readiness và OCR thật | Upload PNG/JPEG synthetic; thử provider thiếu/hỏng | Real pipeline có provenance/spans; lỗi provider không fallback fixture, không bịa confidence | [native workflow](../../scripts/verify_product.py), product tests, [pipeline tests](../../pipeline/tests/test_pipeline.py) |
| R1 — sửa/null/reload | Xóa seller, lưu nháp, tải lại; bổ sung lại giá trị | Explicit null không rơi về prediction; confirm thiếu trường bị chặn; prediction gốc bất biến | Product tests; [ReviewPanel tests](../../frontend/src/features/documents/ReviewPanel.test.tsx); [browser E2E](../../frontend/e2e/invoice.spec.ts) |
| R2 — hai người sửa cùng revision | Hai tab/client cùng revision; lưu A rồi lưu B | B nhận 409, UI giữ edits để so sánh; không silent overwrite | Product concurrent_saves/clear_null tests; ReviewPanel tests; browser E2E kiểm stale request qua API, không thay cho thử hai tab UI |
| C1 — validation và export authority | Confirm draft sai/null; gửi approved từ client; confirm hợp lệ rồi tải JSON | 422/409 theo contract cho dữ liệu sai/stale; export từ latest persisted confirmed revision, values đúng kiểu | Product tests, native workflow, browser E2E |
| H1 — reprocess/history/restart | OCR lại; mở run cũ; thử export run cũ; khởi động lại trên DB tạm | History/prediction/review cũ còn; run cũ chỉ đọc, export stale bị từ chối; dữ liệu đã lưu còn sau restart | Product tests, retry regression, native workflow |
| B1 — backup/restore | Backup runtime tạm rồi restore vào đường dẫn mới; kiểm hashes | Restore giữ revisions/files; từ chối dữ liệu sửa sai hash, không ghi đè runtime đang chạy | Product test backup_restore; [backup helper](../../scripts/backup_runtime.py); không tự gọi là có browser coverage |
| G1 — dữ liệu và evaluator | Kiểm manifest/splits/hashes, chạy frozen evaluator replay | Không overlap parent trái split, không gold trong inference; metrics đúng công thức; replay không phải inference mới | [data checker](../../scripts/check_data.py), [evaluator regression](../../scripts/check_evaluation_regression.py), [evaluation protocol](../ml/evaluation-protocol.md) |

Ca O1 phải đối chiếu preview và spans trên mẫu phát triển bằng mắt khi nghiệm thu giao diện; chỉ kiểm spans non-empty không chứng minh evidence đúng vị trí. Hai tab UI, ảnh khác layout, network recovery trên máy khác và Docker cần kết quả riêng nếu chưa được test tự động bao phủ.

## Các ca còn chờ tích hợp

| Ca | Dependency | Cách nghiệm thu khi code sẵn sàng | Trạng thái tại lúc lập checklist |
|---|---|---|---|
| N1 — notification sau commit | [PR #18](https://github.com/teamfuturetime/document-inteligence/pull/18), #10 | Sender lỗi/timeout không đổi confirmation/export; invalid/rollback không gửi; retry không phát lại; payload/log không chứa fields/source | Pending trên main; log local best-effort, không hứa durable/exactly-once |
| P1 — PDF hợp lệ và evidence | #6, spec PDF được review | Một trang synthetic, OCR thật, preview/render và evidence cùng frame; review→confirm→export; giữ PNG/JPEG/application regression | Pending, chưa chốt limits/error mapping thay Quang |
| P2 — PDF bị từ chối | #6, spec PDF được review | PDF mã hóa/nhiều trang/hỏng/quá budget/timeout: lỗi theo spec và không records/files rác; slot/retry hồi phục | Pending, không lấy kết quả PNG để đánh dấu PDF pass |
| A1 — autosave và ACK cũ | #7 | Sửa liên tiếp A→B, cố tình delay ACK A; B không bị thay bằng A; null giữ đúng; saving/saved/error đúng | Pending, main hiện chỉ manual save |
| A2 — autosave và conflict/navigation | #7 | Hai tab stale409, mất mạng/retry, chuyển tài liệu/unmount khi đang lưu; edits không sang tài liệu khác hoặc mất im lặng | Pending; thử hai tab trình duyệt thật ngoài component mocks |
| X1 — PDF + autosave + confirm/export | #6 + #7 + N1 nếu dùng notification | Upload PDF→sửa→chờ autosave ACK→confirm→download; pending/error không bị coi đã lưu; export khớp revision; notification lỗi không đổi business result | Pending, chỉ chạy khi các dependencies được tích hợp trên cùng SHA |

Đây là yêu cầu nghiệm thu, không phải quyết định triển khai UI/API mới. Nếu spec tính năng đổi hành vi, tác giả cập nhật acceptance trên issue và tests theo contract được review trước khi thay expected results. Không sửa gold/threshold để làm test xanh.

## Lệnh tái chạy

Từ root, dùng runtime pins theo README:

```sh
python scripts/dev.py check
python scripts/dev.py models
uv run --project backend --locked python scripts/verify_product.py --output runtime/verification/product-native-acceptance.json
uv run --project backend --locked python scripts/check_upload_ingress.py --output runtime/verification/upload-ingress-acceptance.json
npm --prefix frontend exec -- playwright install chromium
python scripts/dev.py e2e
```

Chọn đường dẫn report mới cho mỗi lượt để giữ mốc cũ, nhất là ingress helper từ chối ghi đè. `check` có tests với pipeline doubles và frozen predictions; native helper gọi Tesseract thật, scripted review không đo accuracy. Probe ingress dùng provider unconfigured và timeout ngắn để thử lỗi, không đo OCR hoặc SLA. Browser E2E hiện có một invoice workflow; không coi nó bao phủ các ca Pending.

## Ghi kết quả và quyết định tích hợp

Với mỗi lượt, ghi SHA/dirty state, runtime, engine/model/config hashes, lệnh/exit code, ca nào đạt/chưa chạy và lý do. Chỉ lưu báo cáo kỹ thuật gọn/metadata không nhạy cảm khi cần review; raw runtime giữ ngoài Git. CI phải completed/success trên SHA mới nhất và reviewer độc lập xác nhận phần mình kiểm tra trước đề xuất merge. Sau merge một PR, PR còn lại có thể BEHIND: cập nhật và kiểm tra lại phần giao nhau.

Checklist chỉ hoàn tất nghiệm thu nền hiện hành khi các ca tương ứng đã chạy đạt; PDF/autosave/notification vẫn là Pending đến lúc có kết quả cùng source tích hợp. Issue #21 hoàn tất phần chuẩn bị khi tài liệu và baseline được review/merge, không tự đóng issues tính năng #5/#6/#7/#10.
