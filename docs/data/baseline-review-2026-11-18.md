# Review mẫu nhãn và provenance — issue #5

Ngày kiểm tra: 18/11/2026, Asia/Saigon. Phạm vi: CONS-02 / [issue #5](https://github.com/teamfuturetime/document-inteligence/issues/5). Nền `main@fdf757c7f730a52e86bcef9c81f96dd1ae699f1a`, kế thừa dataset của nhatquang; dependency CONS-01 / #4 đã hoàn tất qua PR #3.

## Ai đã kiểm tra và kết luận có giới hạn

Codex thực hiện audit tự động và mở trực tiếp 18 PNG gốc bằng công cụ xem ảnh, đối chiếu với annotation trong phiên làm việc do tài khoản `tuanqtb123-creator` yêu cầu. Không ghi nhận tài khoản này hoặc thành viên nào đã tự xem ảnh hay approve khi chưa có bằng chứng. Người tạo dataset không được tính là reviewer độc lập trong lượt này; chưa có xác nhận review con người trên PR.

Không thấy bất đồng ảnh–nhãn trong **18 mẫu / 108 trường** đã xem: 104 present, 2 absent, 2 unreadable. Audit toàn bộ 150 mẫu chỉ chứng minh những điều kiện máy kiểm được. Không kết luận 150 ảnh đã được review trực quan, nhãn đã được hai người nghiệm thu, hoặc độ chính xác trên hóa đơn thật. Reviewer thực tế cần kiểm chứng kết luận này trên PR; ghi tên/phạm vi bằng chính tài khoản review của mình.

## Cách chọn và đối chiếu mẫu

Chọn các chỉ số `000, 001, 002, 003, 004, 005, 006, 010, 011` cho mỗi loại `hoa_don` và `don_de_nghi`, dựa trên metadata layout/split/quality tags. Tập mẫu phủ đủ 2 loại × 3 layout × 3 split; bổ sung masked, absent, invalid-calendar và mild-blur. Không chọn theo prediction errors. Đã đọc mô tả generator và báo cáo baseline trước khi đối chiếu; không gọi đây là nghiên cứu blinded. Không mở predictions để quyết định sửa nhãn hoặc chọn mẫu, không tune holdout.

Mỗi PNG được xem nguyên trang, kiểm watermark synthetic, chữ/dấu/số 0, nội dung đọc được, vùng trống/che và dấu hiệu crop/tràn; sau đó so với giá trị/status/type trong JSON. Ngày hợp lệ trên ảnh dd/mm/yyyy được so với ISO trong gold; ngày không tồn tại được giữ nguyên. Không suy lại giá trị bị che từ seed/generator. Quy tắc ở [annotation guide](annotation-guide.md) và [protocol](../ml/evaluation-protocol.md).

### Hóa đơn: toàn bộ 5 trường mỗi mẫu

Đường dẫn ảnh/nhãn tương ứng là `data/product/images/<ID>.png` và `data/product/annotations/<ID>.json`; hashes nằm trong manifest đã pin. Mọi mẫu dưới đều có `currency=VND`; các số tiền được ghi trong gold bằng integer VND, không chuỗi có dấu phân cách.

| Sample | Split / layout | Nội dung đối chiếu trực tiếp trên ảnh | Kết quả |
| --- | --- | --- | --- |
| hoa_don_000 | test / 0 | `0041000`; `01/10/2026`; `Công ty Giả Lập 100`; `125.000` | 5 trường khớp, giữ số 0 |
| hoa_don_001 | validation / 1 | `0041001`; `02/10/2026`; `Công ty Giả Lập 101`; `250.000` | 5 trường khớp |
| hoa_don_002 | development / 2 | `0041002`; `03/10/2026`; seller bị che bằng khối xám; `375.000` | seller unreadable/null, 4 trường còn lại khớp |
| hoa_don_003 | development / 0 | `0041003`; `04/10/2026`; seller để trống dưới nhãn; `500.000` | seller absent/null, 4 trường còn lại khớp |
| hoa_don_004 | development / 1 | `0041004`; **`31/02/2026`**; `Công ty Giả Lập 104`; `625.000` | 5 trường khớp; gold giữ ngày sai nhìn thấy |
| hoa_don_005 | test / 2 | `0041005`; `06/10/2026`; `Công ty Giả Lập 105`; `750.000`, ảnh hơi mờ vẫn đọc được | 5 trường khớp |
| hoa_don_006 | validation / 0 | `0041006`; `07/10/2026`; `Công ty Giả Lập 106`; `875.000` | 5 trường khớp |
| hoa_don_010 | test / 1 | `0041010`; `11/10/2026`; `Công ty Giả Lập 110`; `1.375.000` | 5 trường khớp, gold amount `1375000` |
| hoa_don_011 | validation / 2 | `0041011`; `12/10/2026`; `Công ty Giả Lập 111`; `1.500.000` | 5 trường khớp, gold amount `1500000` |

### Đơn đề nghị: toàn bộ 7 trường mỗi mẫu

Mọi mẫu có khoa **Công nghệ thông tin** và nội dung **Đề nghị cấp giấy xác nhận đang theo học. Mã hồ sơ mẫu N.**, với N tương ứng cột tên. Đã đối chiếu cả dấu tiếng Việt và dấu chấm cuối, không chỉ ID/ngày. Giá trị ngày dưới đây là chữ trên ảnh; gold dùng ISO trừ ngày sai.

| Sample | Split / layout | Tên / mã sinh viên | Ngày sinh / lớp / ngày làm đơn | Kết quả |
| --- | --- | --- | --- | --- |
| don_de_nghi_000 | test / 0 | Nguyễn Minh An 100 / `00100000` | 01/03/2005 / CNTT-K16 / 01/10/2026 | 7 trường khớp |
| don_de_nghi_001 | validation / 1 | Nguyễn Minh An 101 / `00100001` | 02/03/2005 / CNTT-K17 / 02/10/2026 | 7 trường khớp |
| don_de_nghi_002 | development / 2 | Nguyễn Minh An 102 / mã bị che bằng khối xám | 03/03/2005 / CNTT-K18 / 03/10/2026 | student_id unreadable/null; 6 trường còn lại khớp |
| don_de_nghi_003 | development / 0 | Nguyễn Minh An 103 / vùng mã để trống | 04/03/2005 / CNTT-K19 / 04/10/2026 | student_id absent/null; 6 trường còn lại khớp |
| don_de_nghi_004 | development / 1 | Nguyễn Minh An 104 / `00100004` | 05/03/2005 / CNTT-K20 / **31/02/2026** | 7 trường khớp, giữ ngày sai nguồn |
| don_de_nghi_005 | test / 2 | Nguyễn Minh An 105 / `00100005` | 06/03/2005 / CNTT-K16 / 06/10/2026 | 7 trường khớp, mild blur vẫn đọc được |
| don_de_nghi_006 | validation / 0 | Nguyễn Minh An 106 / `00100006` | 07/03/2005 / CNTT-K17 / 07/10/2026 | 7 trường khớp |
| don_de_nghi_010 | test / 1 | Nguyễn Minh An 110 / `00100010` | 11/03/2005 / CNTT-K16 / 11/10/2026 | 7 trường khớp |
| don_de_nghi_011 | validation / 2 | Nguyễn Minh An 111 / `00100011` | 12/03/2005 / CNTT-K17 / 12/10/2026 | 7 trường khớp |

## Audit toàn bộ và tái lập

Chạy từ root theo môi trường lockfile trong README:

```sh
uv run --project backend --locked python scripts/audit_product_data.py --output runtime/data-qa/my-new-audit.json
uv run --project backend --locked python scripts/check_data.py
uv run --project backend --locked python scripts/check_evaluation_regression.py
```

`--output` phải là file mới; không ghi đè báo cáo cũ. Bỏ tùy chọn để in JSON ra stdout. Audit không mở predictions, không sửa dataset và không chạy inference. `check_data.py` dùng cùng audit nên CI backend hiện có sẽ chặn drift nhãn.

Kết quả kiểm kê tái lập trong [JSON evidence](../evidence/baseline-data-qa-2026-11-18.json):

- 150 ảnh/150 annotation/150 parent IDs độc nhất; 75 hóa đơn + 75 đơn; 90 development, 30 validation, 30 test (mỗi loại 45/15/15).
- 900 nhãn: 882 present, 10 absent, 8 unreadable. Trường không đọc được/không có đều null; kiểm đủ keys/ID/status/type, NFC/whitespace; integer không chấp nhận boolean. Ngày sai nguồn vẫn là text hợp lệ cho gold, không áp final business validation lên annotation.
- Paths và SHA256 ảnh/annotation khớp manifest; không trùng input bytes, không parent chéo split, không canonical label content trùng chéo split. Đây không phải detector ảnh gần trùng hoặc bảo đảm semantic uniqueness.
- Cả 6 template IDs xuất hiện trong cả 3 splits. Điểm frozen đo trên cùng họ layout; không được diễn giải thành unseen-layout accuracy.

## Fingerprints được giữ nguyên

Không sửa manifest/ảnh/annotation trong `data/`, generator, pipeline/rules/config/model lock, predictions hoặc report frozen; chỉ bổ sung liên kết báo cáo trong dataset README. JSON evidence lưu hashes của các file baseline và bản sao nguyên metadata run từ report; đối chiếu với Git diff trước commit. Không tạo benchmark native mới trong task này.

| Fingerprint | Giá trị baseline |
| --- | --- |
| Dataset | `product-synthetic-1.0.0` |
| Manifest SHA256 | `3e5cf4c039b7c4f678ba3a5c3ac39a8b0aa7b921f9d1923b2040053f04d3ccdb` |
| Frozen run ID | `0c2a99f6fa474616a63b3bacd161f750` |
| Tesseract / platform | `5.4.0.20240606` / Windows AMD64 CPU |
| Model revision | `87416418657359cb625c412a48b6e1d6d41c29bd` |
| Pipeline source SHA256 | `8576b1df9b1d327f5119f6d8ae686920a2a7f4469363b1a73b828f5bbae33fcf` |
| Config version / SHA256 | `inference-config-1.1.0` / `3615bd047d1f1e3897482040368f991002d12cfc9bc2e8a9591e871308d1b5ff` |

Frozen report ghi `git_commit=f37bfbdbb6c4669c8a867d15610129fb7d351928` và `git_dirty=true`; đây là trạng thái lúc inference gốc, không thay bằng SHA sạch hiện tại. Giữ source hash để phân biệt. Replay 30 documents đạt với đúng membership/gold/metrics cũ, `new_inference=false`; không suy rằng engine hiện tại hoặc Linux/macOS có cùng kết quả.

## Kiểm chứng thay đổi

Windows, CPython 3.14.5, uv 0.12.22 và dependencies theo `backend/uv.lock`; Node 24.16.0/npm 11.13.0 và `frontend/package-lock.json`. Công cụ mới nằm trong runtime local; không sửa phiên bản toàn hệ thống.

| Check đã chạy | Kết quả |
| --- | --- |
| `python scripts/dev.py backend-check` | Ruff check/format pass; **184 backend/pipeline tests pass**, gồm 20 ca audit mới; 25 contracts; 6 fixtures + 150 product samples pass |
| `python scripts/dev.py evaluation-check` | Frozen replay 30 documents và fixture evaluator contract check pass; không inference mới |
| `python scripts/dev.py frontend-check` | Không chạy hết entry point: Windows `subprocess.run(["npm", ...])` báo `[WinError 2]` vì npm là `.cmd` |
| 6 npm scripts tương đương bằng `node <npm-cli.js> --prefix frontend run <script>` | `contracts:check`, `typecheck`, `lint`, `format:check`, **12 component tests**, production `build` đều pass |
| Audit CLI output mới / lặp cùng output | Tạo JSON thành công; lần lặp bị từ chối `FileExistsError`, bytes báo cáo cũ không đổi |
| Evidence vs audit/manifest/baseline | JSON audit trùng kết quả chạy lại; tất cả file hashes baseline và 18 tổ hợp type/layout/split khớp |
| `python scripts/check_repository.py` | 86 Markdown files, links/config/YAML/Action refs pass sau bổ sung báo cáo |

Không chạy `ocr` hoặc browser E2E local vì task chỉ thêm audit offline/tài liệu, không sửa đường OCR/API/UI. Product CI vẫn chạy mọi job cho PR; xem kết quả đúng head/merge SHA trên PR, không coi kết quả local này là remote CI đã pass. Lỗi entry point Windows được ghi nhận riêng tại [issue #34](https://github.com/teamfuturetime/document-inteligence/issues/34) sau khi tìm issue trùng; không sửa lẫn vào data QA.

## Phần reviewer cần quyết định

Reviewer con người xác nhận mẫu/ghi bất đồng bằng tài khoản thật trước khi coi review chéo cuối cùng hoàn tất. Không tự bổ sung tên người review vào dataset card hoặc sửa gold theo máy. Nếu phát hiện bất đồng, ghi sample/field và ảnh nguồn trước; cập nhật nhãn/version/evidence ở thay đổi được duyệt riêng.

Unseen-layout nên là **dataset version mới** có template families và parent groups được tách trước khi render/biến đổi, review nhãn dựa trên ảnh, chọn config chỉ trên development/validation, đóng băng layout test mới và lưu run vào thư mục mới. Không đổi splits/hashes của v1 hoặc tune trên 30 test hiện tại. Task này chỉ đề xuất protocol; chưa tạo ảnh mới hay tuyên bố đo unseen-layout/ảnh thật.
