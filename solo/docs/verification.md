# Bằng chứng local — 2026-11-11

Bản ứng dụng cá nhân mới đã triển khai và kiểm thử ở commit code sạch
`65a0816546103aaf0b07ae72b1bc5382b6487745`. Bản tích hợp và main chung giữ nguyên.
Các commit sau checkpoint này lưu baseline/tài liệu; hash source trong report
cho phép xác định đúng code AI được đo, không dựa riêng vào tên nhánh.

## Chức năng và kiểm tra

- 41 Python tests đạt khi đặt `SOLO_RUN_OCR=1`, gồm sáu native OCR cases cho
  hai loại tài liệu × PNG/JPEG/PDF; mặc định skip rõ sáu ca native.
- 4 UI tests đạt: edit làm mất validation cũ, response extraction/validation
  trễ không ghi đè state mới, VLM chưa cấu hình/oversize không gọi nhầm rules.
- TypeScript và production build đạt.
- 7 Playwright E2E đạt bằng Chrome local: sáu flow OCR thật → sửa → validate
  → tải JSON; một ca mobile preview không tràn ngang + corrupt document báo lỗi.
  Download được đọc lại, so sánh final values, original extraction, edited_fields.
- Đã xem ảnh screenshot desktop review và mobile 390px; ảnh runtime ở
  `web/test-results/`, không commit vào mã nguồn.
- Từ git archive chỉ chứa `solo/` ở `/private/tmp/ai02-solo-clean.5bL40V`: uv sync
  --locked --offline tạo venv mới; 35 Python tests đạt, sáu native skip. npm ci
  --offline tạo node_modules mới; UI tests/typecheck/build đạt. Không cần các
  package implementation cũ để chạy ứng dụng mới; native models được provision
  riêng trong `.models/` của bản mới.
- Workflow `AI-02 Solo` đã cấu hình real OCR/evaluation/UI/E2E và kiểm tra YAML/
  pin action SHA. Kết quả GitHub cần xem đúng SHA của lần push; local pass không
  đồng nghĩa Linux/CI đã pass. Job CI dùng Tesseract 5.3.4, khác host local 5.5.2.

## Baseline OCR + luật

Golden đã freeze ở `93afac7`, gồm 36 tài liệu synthetic / 18 dev + 18 test.
Kết quả trước review trên macOS ARM64, Tesseract 5.5.2, model vie/eng pin SHA:

| Tập | Tài liệu | Macro exact match | Execution error |
| --- | ---: | ---: | ---: |
| Dev | 18 | 0,9000 | 0 |
| Test | 18 | 0,9111 | 0 |
| All | 36 | 0,9056 | 0 |

Trên test: hóa đơn exact match 1,0000; đơn đề nghị 0,8222. Điểm chung không được
dùng để bỏ qua các trường tên/nơi nhận của đơn bị mất dấu. Xem chi tiết mỗi
trường, PRF, null pairs, slices và mismatch trong
[report test](../evaluation/baselines/rules-v1-test.json) và
[report all](../evaluation/baselines/rules-v1-all.json).

Hai lượt all độc lập tạo JSON byte-identical. Source SHA-256:
`cdb27097fe9763449bc9697a2da1d5878ed83d622feeb8806e7fccf5ea275f89`.
Report all SHA-256:
`d8e10036b5101107e7adfb750d1e040ef318cbbb05489af3a48af83cc201498b`.
Có 17 mismatch trên 36 tài liệu, giữ nguyên giá trị sai; không bỏ dấu khi chấm
và không sửa ground truth để nâng điểm. Cause chưa được review độc lập.

## Việc để sau theo phạm vi đã chọn

- Cấu hình model VLM local/API rồi chạy inference/evaluation thật; hiện chỉ
  kiểm thử adapter, chưa có kết quả chất lượng VLM/hybrid.
- Review ground truth và triage nguyên nhân với người khác tác giả; automatic
  tests/AI-assisted review không được tính là review độc lập.
- Tạo challenge set synthetic ngoài ba layout trước khi tuyên bố tổng quát.
  Không suy ra hóa đơn từng upload bị lỗi ở bản cũ đã được sửa cho mọi trường hợp.
- Chưa hỗ trợ chữ viết tay, PDF nhiều trang, bảng nhiều cột hoặc mọi loại đơn.
