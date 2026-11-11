# Bằng chứng local — 2026-11-11

## Chế độ sáng và tối

- 12 UI tests đạt, gồm ba ca theme mới: theo hệ thống trước khi chọn và giữ
  lựa chọn sau đó; giá trị lưu không hợp lệ/đồng bộ tab/xóa lựa chọn; lưu trữ
  bị chặn vẫn chuyển chế độ được. TypeScript và production build đạt.
- Hai browser E2E riêng cho theme đạt bằng Chrome local: theme đã lưu được áp
  dụng trước khi React khởi động và giữ sau tải lại; chuyển sáng/tối sau OCR
  thật vẫn giữ trường đã sửa và nút export đã được validation mở.
- Đã xem ảnh review ở hai chế độ trên desktop/mobile. Ca theme kiểm tra màu
  nền CSS thực tế và không tràn ngang tại 1440, 390 và 320 px. Đây là các ca
  theme bổ sung; tám ca E2E giao diện cũ được ghi nhận ở checkpoint bên dưới.

## Giao diện bàn làm việc

- 9 UI tests và TypeScript/production build đạt. Các ca mới kiểm tra response
  tải mẫu trễ không thay file người dùng vừa chọn, kéo thả file mới hủy kết quả
  đã xác nhận, từ chối nhiều file và cảnh báo trường vẫn hiện khi evidence đóng.
- 8 browser E2E đạt với Chrome local: sáu flow OCR thật cho hai schema ×
  PNG/JPEG/PDF, một flow mobile chọn file bằng bàn phím/hướng dẫn/lỗi ảnh hỏng,
  một flow mẫu có sẵn/zoom/xóa. File JSON tải xuống được đọc lại để so sánh
  final values, original extraction và edited_fields.
- Flow mẫu có sẵn không tự gọi extraction. Mẫu công khai trong frontend là
  bản sao byte-identical của `data/golden-v1/invoice-001.png`.
- Review thật không tràn ngang tại 1440, 820, 768, 390 và 320 px. Font được
  phục vụ nội bộ, có giấy phép OFL và manifest nguồn/hash trong `web/public/fonts/`.
- Không thay backend, dữ liệu golden hoặc baseline. Kiểm thử cloud dùng mock
  để xác nhận selection/confidence/key boundary; không coi đây là lượt chạy
  OCR.space hoặc model VLM thật mới.

## Bổ sung OCR.space

Pipeline `solo-1.1` có hai nguồn OCR; xem [hướng dẫn và bằng chứng live](ocrspace.md).
Đã thử key thật trên PNG/JPEG/PDF synthetic và UI cloud → review → tải JSON,
giữ confidence null và key ở backend. 63 Python tests, 7 UI tests/build và 7 E2E
Tesseract đạt local. Không xem smoke ba mẫu là benchmark cloud; baseline rules
v1/v2 dưới đây vẫn thuộc Tesseract và giữ nguyên dữ liệu/report lịch sử.

## Trạng thái mới nhất — rules v2

Commit code `e203bf7c28e0cbb43cdaf4d6d7a445c2f3027ae1` đã
[pass GitHub CI](https://github.com/teamfuturetime/document-inteligence/actions/runs/42951239678):
43 Python tests (có real OCR), 4 UI tests, typecheck/build và 7 browser E2E.
Golden test trên Ubuntu/Tesseract 5.3.4 đạt **0,9333**, 18 tài liệu, không
execution errors. Trên macOS/Tesseract 5.5.2, cùng code/model/data đạt **0,9111**
trên test. Không coi điểm khác runtime là một kết quả giống nhau.

Sửa lỗi dựa trên **dev** `application-001`: OCR Linux đọc `Mã số sinh viên`
thành `Ma sé sinh vién`; mapping exact bỏ sót ID. Rule v2 chỉ ghép nhãn dài
ít nhất 10 ký tự, có dấu hai chấm, sai tối đa một ký tự và duy nhất một field.
Giữ nguyên giá trị, evidence và cảnh báo; nhãn ngắn/không dấu hai chấm/khớp
mơ hồ không được sửa. Không thay dataset, ground truth hoặc ngưỡng regression.

Baseline macOS v2 mới: [test](../evaluation/baselines/rules-v2-test.json),
[all](../evaluation/baselines/rules-v2-all.json). Metrics macOS không đổi so
với bảng v1 bên dưới; hai lượt all v2 tiếp tục byte-identical. Source SHA-256:
`a51044b140e94a0e5f5cbbf150e1424cbfb8eddc0b2c3dda29cea7390e26efe7`.
Report all v2 SHA-256:
`43f3cf190d7fee7cbd25c49581eb3cb9098c6c997b9319f85c6b4d807447999e`.
Các checkpoint baseline v1 bên dưới được giữ nguyên để thấy lịch sử đo.

## Checkpoint lịch sử — rules v1

Bản ứng dụng cá nhân mới đã triển khai và kiểm thử ở commit code sạch
`65a0816546103aaf0b07ae72b1bc5382b6487745`. Bản tích hợp và main chung giữ nguyên.
Hash source trong từng report xác định đúng code AI được đo, không dựa riêng
vào tên nhánh; code đã tiếp tục được cập nhật thành rules v2 ở trên.

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
- Workflow `AI-02 Solo` có real OCR/evaluation/UI/E2E, YAML và action pin SHA.
  Checkpoint v1 có lỗi Linux đã được sửa ở rules v2 nêu trên; giữ lịch sử lỗi
  thay vì thay đổi assertion/ground truth để làm CI xanh.

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
