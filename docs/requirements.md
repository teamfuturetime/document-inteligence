# Yêu cầu và phạm vi MVP

## Mục tiêu

Hỗ trợ luồng tài liệu mẫu → OCR → trích xuất theo schema → người dùng kiểm tra/sửa
→ backend validation → xác nhận → xuất JSON. Phát triển cá nhân theo từng task nhỏ,
chạy local, có kiểm tra và commit trên `tuannguyen`.

## Trạng thái trước S2.1

S1.1 và S1.2 có commit local; frontend mới được kiểm tra CLI/build/HTTP và render
trong Node. **Chưa có kết quả kiểm tra trực quan desktop/mobile hoặc browser console**;
không đánh dấu toàn bộ Giai đoạn 1 đã kiểm thử đầy đủ. Xem [testing.md](testing.md).
S2.1 chỉ chốt thiết kế dữ liệu, không bổ sung chức năng hoặc tuyên bố đã kiểm thử UI.

## Quyết định MVP tại S2.1

Chọn duy nhất **hóa đơn bán hàng tiếng Việt một trang, dữ liệu tổng hợp**, ảnh
PNG/JPEG, nội dung in máy theo quy ước nguồn `vi-VN`. Mã loại tài liệu:
`sales_invoice`; phiên bản đặc tả: `schema_version = "1.0.0"`.
S2.1a đã hiện thực và kiểm thử hai model giá trị canonical `InvoiceValues` và
`FinalInvoiceValues` bằng Pydantic. Các envelope OCR/extraction/validation/review
bên dưới vẫn là thiết kế, chưa có class/API hoặc file JSON Schema xuất riêng.

MVP chỉ lấy thông tin đầu hóa đơn và tổng tiền cuối cùng phải trả. PDF, nhiều trang,
bảng chi tiết hàng hóa, thuế/chiết khấu, thông tin người mua, mã số thuế, chữ viết tay
và các loại đơn khác nằm ngoài schema 1.0.0. Không xác minh tính pháp lý/kế toán
của hóa đơn. OCR và VLM thật vẫn là yêu cầu cho giai đoạn tích hợp; fake provider
hoặc extraction theo luật chỉ hỗ trợ phát triển và baseline.

### Giá trị chuẩn hóa và trường bắt buộc

Hai dạng giá trị dùng cùng **năm key bắt buộc**, không chấp nhận key lạ:

- `InvoiceValues`: mỗi giá trị có thể `null`, dành cho kết quả máy/bản chuẩn hóa còn lỗi.
- `FinalInvoiceValues`: cả năm giá trị phải khác `null` và thỏa bảng dưới; dành cho
  bản hợp lệ, chưa tự mang nghĩa người dùng đã xác nhận.

Schema MVP không có trường nghiệp vụ tùy chọn. Metadata như vị trí OCR và confidence
có thể không có cơ sở để cung cấp; biểu diễn bằng `null`, không bịa thông tin.
Key bị bỏ quên là lỗi contract, khác với key tồn tại nhưng giá trị `null`.
Hai model value không chứa `status`, `warnings`, `confidence`, metadata schema hoặc
cờ xác nhận. Các thuộc tính đó thuộc envelope ở phần sau; thêm chúng vào value model
là lỗi key lạ. `FinalInvoiceValues` hợp lệ không chứng minh người dùng đã xác nhận.

| Trường | Kiểu JSON chuẩn hóa, giới hạn | Ý nghĩa / bắt buộc ở bản cuối |
| --- | --- | --- |
| `invoice_number` | `string`, 1–100 ký tự ASCII, full-match pattern `^[A-Za-z0-9][A-Za-z0-9./_-]{0,99}$` | Số/mã hóa đơn; giữ số 0 đầu, chữ hoa/thường và dấu phân cách. Bắt buộc. |
| `invoice_date` | `string`, đúng `YYYY-MM-DD`, ngày lịch hợp lệ, năm 0001–9999; không có giờ/múi giờ | Ngày lập trên hóa đơn, không phải thời điểm OCR. Bắt buộc. |
| `seller_name` | `string` Unicode NFC, 1–200 code point sau chuẩn hóa; có ít nhất một chữ cái | Tên đơn vị bán; giữ dấu tiếng Việt và hoa/thường. Bắt buộc. |
| `total_amount` | JSON integer, `0 <= value <= 9007199254740991` | Tổng tiền cuối phải trả, đơn vị đồng; 0 là giá trị có thật. Bắt buộc. |
| `currency` | `string`, chỉ nhận `"VND"` | Đơn vị tiền có chứng cứ hoặc do người dùng điền/xác nhận. Bắt buộc. |

Giới hạn tiền là `2^53 - 1` để trao đổi số nguyên chính xác với JavaScript, không phải
giới hạn nghiệp vụ/kế toán. Canonical model kiểm tra kiểu strict: không biến số hóa đơn
thành số, không nhận boolean như số nguyên, không nhận float hoặc chuỗi thay integer.
Không có default tự lấp dữ liệu. Chuỗi canonical không có khoảng trắng thừa hay ký tự
điều khiển (Unicode category `Cc`, `Cf`, `Cs`); chuẩn hóa input thô là bước riêng
trước kiểm tra canonical model. Tên người bán canonical đã ở NFC, khoảng trắng bên
trong chỉ là dấu cách đơn U+0020; model từ chối bản chưa chuẩn hóa, không tự sửa nó.

Ví dụ **giá trị chuẩn hóa tổng hợp** (không phải output đã chạy OCR hoặc đã duyệt):

```json
{
  "invoice_number": "HD-0000123",
  "invoice_date": "2026-04-03",
  "seller_name": "Cửa hàng Mây Việt — DỮ LIỆU GIẢ",
  "total_amount": 125000,
  "currency": "VND"
}
```

### Quy tắc chuẩn hóa input thô

Luôn giữ nguyên text/giá trị nguồn để truy vết. Chỉ chuẩn hóa bản sao; không sửa nội dung
OCR gốc. Chuỗi được chuyển Unicode NFC và trim khoảng trắng đầu/cuối. Với tên người bán,
gộp chuỗi khoảng trắng (kể cả xuống dòng) thành một dấu cách. Với các trường còn lại,
không tùy tiện xóa ký tự bên trong. Ký tự điều khiển không thuộc khoảng trắng hợp lệ
bị báo lỗi. Chuỗi rỗng/sau trim chỉ còn trắng được xem là thiếu, không trở thành số 0.

| Trường hợp nguồn | Quyết định chuẩn hóa / xử lý |
| --- | --- |
| Số hóa đơn `" 0000123 "`, `"HD-0000123"` | Thành `"0000123"`, `"HD-0000123"`; giữ nguyên số 0 đầu. Không parse integer, không đổi `O` thành `0`, không bỏ khoảng trắng bên trong để tự sửa mã sai. |
| Ngày `"03/04/2026"` | Nguồn MVP quy ước **DD/MM/YYYY**, nên thành `"2026-04-03"`; không thử đảo thành tháng/ngày. Chỉ nhận đủ hai chữ số ngày/tháng và bốn chữ số năm. |
| Ngày `"2026-04-03"` | Đã theo ISO; giữ nguyên sau kiểm tra ngày có thật. |
| Ngày `"31/04/2026"`, `"2026-02-29"`, `"01/02/03"` | Hai ví dụ đầu là ngày không tồn tại, ví dụ cuối sai định dạng; không đoán/sửa thành ngày khác. Không lấy ngày hiện tại làm default. |
| Ngày từ nguồn chưa rõ quy ước | Không áp dụng DD/MM chỉ vì ngôn ngữ tài liệu; đánh dấu `uncertain` để người dùng quyết định. Nguồn ngoài phạm vi MVP không được chấp nhận ngầm. |
| Tiền `"125000"`, `"125.000"`, `"1.250.000"` | Chấp nhận chữ số ASCII, hoặc nhóm nghìn bằng **dấu chấm**, mỗi nhóm sau đầu có đúng ba chữ số; thành 125000, 125000, 1250000. Nhóm đầu 1–3 chữ số, bắt đầu 1–9; chuỗi không nhóm có thể có số 0 đầu. |
| Tiền `"125.000 ₫"`, `"125000 VND"` | Tách hậu tố tiền tệ ở cuối chuỗi, trim phần số rồi áp dụng quy tắc trên; chính hậu tố là evidence cho `currency`. Giữ text nguồn cho cả hai trường. |
| Tiền `"125,000"` | Dấu phẩy có thể mang nhiều cách đọc ở nguồn khác quy ước: `uncertain`/`ambiguous_amount`, value null. Không đoán thành 125000 hoặc 125. |
| Tiền `"1,5 triệu"`, `"125 000"`, `"125.00"` | Ngoài định dạng MVP hoặc nhóm nghìn sai: `invalid`/`invalid_amount_format`, value null. Không quy đổi đơn vị viết tắt hay tự sửa dấu phân cách. |
| Tiền âm, float, ký pháp mũ, boolean hoặc vượt giới hạn | Không hợp lệ. Bản thô là chuỗi có thể được parse theo quy tắc; canonical JSON phải là integer. Không nhân/chia 100, không làm tròn hoặc dùng float trung gian. |
| Currency `"VND"`, `"VNĐ"`, `"đồng"`, `"đ"`, `"₫"` | So khớp không phân biệt hoa/thường sau NFC/trim, chuẩn hóa thành `"VND"`. Không suy từ việc tài liệu viết tiếng Việt. |
| Không có currency; chỉ có ký hiệu `"d"`; có USD hoặc nhiều currency mâu thuẫn | Thiếu thì `missing`; `d` đơn lẻ hoặc mâu thuẫn thì `uncertain`; USD ghi rõ là `invalid`/`unsupported_currency`. Không đổi ngoại tệ, không mặc định VND. |

Hậu tố tiền tệ chỉ được tách nếu thuộc danh sách VND ở trên. Khi có nhiều tổng tiền
khác nhau mà không xác định được nhãn tổng cuối phải trả, không chọn số lớn nhất;
đánh dấu `uncertain`. Cần người dùng sửa/điền trường rồi xác nhận bản hợp lệ.
Các phép chuyển đổi input thô ở bảng này **chưa được code hoặc test tự động**;
S2.1a chỉ kiểm tra giá trị đã canonical và từ chối dữ liệu chưa chuẩn hóa, không tự sửa.
Kích thước file/pixel/timeout vẫn để task upload/provider chốt, không thêm vào schema
nghiệp vụ ở S2.1a.

### Dữ liệu trích xuất và trường thiếu/không chắc chắn

`ExtractionResult.fields` luôn có đủ năm trường. Mỗi `ExtractedField<T>` gồm:

| Thuộc tính | Kiểu / ý nghĩa |
| --- | --- |
| `raw_value` | `string \| null`, text nguồn trước chuẩn hóa; rỗng nếu nguồn thật sự để trống. |
| `value` | `T \| null`, với T theo bảng giá trị canonical. |
| `status` | `candidate`, `missing`, `uncertain` hoặc `invalid`. |
| `evidence` | Danh sách `{id: string, text: string, page: 1, bbox: object \| null}` tham chiếu nguồn; mảng rỗng khi chưa có chứng cứ. Quy ước bbox ở architecture. |
| `confidence` | `FieldConfidence \| null`; mặc định của các ví dụ/fake là null, không dùng 0 để diễn đạt chưa biết. |
| `warnings` | Danh sách mã, ví dụ `missing_field`, `ambiguous_amount`, `ambiguous_field`, `invalid_date`, `unsupported_currency`, `no_evidence`. |

- `candidate`: có giá trị canonical khác null, raw text và evidence truy vết được;
  vẫn là dự đoán, chưa phải dữ liệu đúng hay đã được người dùng duyệt.
- `missing`: không có nội dung cho trường; value/confidence null. Evidence có thể
  chỉ nhãn trống; không tự điền từ thông tin ngoài tài liệu.
- `uncertain`: nhiều ứng viên, quy ước chưa rõ hoặc không có evidence đủ để chọn;
  value/confidence null, giữ raw text/evidence/cảnh báo để review.
- `invalid`: đọc được nội dung nhưng vi phạm định dạng/giới hạn đã chốt;
  value/confidence null, giữ nguyên nguồn và mã lỗi.

Mọi thuộc tính của `ExtractedField` ở bảng đều phải có key, kể cả khi null hoặc mảng rỗng;
các trạng thái khác `candidate` có ít nhất một warning giải thích lý do. Không dùng
chuỗi `"null"` hoặc chuỗi rỗng làm giá trị canonical cho trường bị thiếu.

Không dùng threshold confidence chưa được đánh giá để tự quyết định trạng thái.
Ví dụ minh họa một trường nhập nhằng, **không phải toàn bộ ExtractionResult**:

```json
{
  "raw_value": "125,000",
  "value": null,
  "status": "uncertain",
  "evidence": [{"id": "e1", "text": "125,000", "page": 1, "bbox": null}],
  "confidence": null,
  "warnings": ["ambiguous_amount"]
}
```

### Field-level confidence

Khi có cơ sở, `FieldConfidence` là object có `score` (số hữu hạn trong [0, 1]),
`source` (`ocr_aggregation` hoặc `calibrated_extraction`), `method_version` (chuỗi
không rỗng), `calibration_version` (chuỗi hoặc null), `evidence_ids` (danh sách ID
evidence thuộc chính trường đó). Score chỉ được gắn cho `candidate` có value;
các trạng thái còn lại phải để confidence null.

Chưa chọn hoặc đánh giá phương pháp nào, nên **confidence cấp trường hiện chưa có
điểm số; tất cả ví dụ để null**. Sau này chỉ dùng `ocr_aggregation` khi có score OCR
gắn token/span và quy tắc tổng hợp/version công khai; điểm đó không phải xác suất
giá trị trường đúng. `calibrated_extraction` phải có calibration version và bằng chứng
đánh giá. Điểm VLM tự báo chưa được kiểm chứng không được gán vào field confidence.
Score OCR native giữ ở OCRResult kèm thang đo và nguồn, không chia 100 hoặc đổi tên
thành field confidence ngầm. Điểm 0 chỉ mang nghĩa số đo thực sự bằng 0.

Việc người dùng xác nhận/sửa là provenance của review, không tạo confidence 1.0;
confidence gốc chỉ thuộc extraction gốc, không chuyển sang giá trị đã sửa.

### Giả định và vấn đề còn mở

- Mẫu tổng hợp sẽ ghi rõ nguồn `vi-VN`, ngày DD/MM/YYYY, tiền nguyên VND, nhãn tổng tiền
  cuối và dữ liệu được phép sử dụng. Chưa có dataset nên đây chưa phải bằng chứng R07/R09 hoàn thành.
- Tài liệu thật không đúng quy ước, tiền thập phân/ngoại tệ và số hóa đơn ngoài tập ký tự
  trên cần mở rộng schema có version sau, không âm thầm nới quy tắc.
- Chưa chọn OCR/VLM, phương pháp confidence, ngưỡng review hoặc giới hạn file/timeout.
- Đã có hai model Pydantic canonical và test offline; chưa có normalization service,
  validation API, extraction metadata/confidence hoặc review/export thực thi.
  [Architecture](architecture.md) chốt ranh giới; task service input thô tiếp theo là S2.2.

## Theo dõi đủ yêu cầu giảng viên

Trạng thái chỉ phản ánh nhánh `tuannguyen`. Viết tài liệu hoặc có code trên remote
không đồng nghĩa đã triển khai. Trạng thái dùng: **chưa triển khai**, **đang triển khai**,
**đã triển khai**, **đã kiểm thử**. Chỉ dùng trạng thái cuối khi có kết quả chạy kiểm tra
phù hợp, chỉ rõ phạm vi và phiên bản.

| ID | Yêu cầu | Giai đoạn / task | Bằng chứng cần để xác nhận | Trạng thái |
| --- | --- | --- | --- | --- |
| R01 | OCR nội dung tài liệu | 3 / S3.1–S3.2 | Chạy OCR thật trên ảnh mẫu; xử lý lỗi; test fake offline. | Chưa triển khai |
| R02 | Schema extraction | 2–3 / S2.1, S2.1a, S3.1, S3.3 | Output có schema; trích xuất từ tài liệu; test thiếu/sai trường. | Đang triển khai: hai model value đã kiểm thử; chưa extraction envelope/inference. |
| R03 | Confidence cấp trường khi có cơ sở | 3–4 / S3.3, S4.2 | Ghi nguồn/cách tính; test null khi không có cơ sở; UI giải thích điểm. | Chưa triển khai |
| R04 | Review UI có chỉnh sửa | 4 / S4.2 | Test hiển thị và sửa từng trường; giữ kết quả trích xuất gốc. | Chưa triển khai |
| R05 | Schema và business validation | 2, 4 / S2.1a–S2.2, S4.3 | Unit test và API test; backend từ chối dữ liệu sai. | Đang triển khai: canonical model validation đã kiểm thử; chưa normalize/business service hoặc validation API. |
| R06 | Export JSON đã kiểm tra/chỉnh sửa | 4 / S4.4 | Export phản ánh sửa đổi; từ chối bản chưa hợp lệ/chưa xác nhận; test JSON. | Chưa triển khai |
| R07 | Chỉ dùng dữ liệu tổng hợp/được phép | 3, 5 / S3.2, S5.1 | Manifest có nguồn, quyền sử dụng, hash; rà soát ảnh và ground truth. | Chưa triển khai |
| R08 | Python, OCR, VLM và React/Vue | 1, 3 / S1.1–S1.2, S3.2–S3.3 | Backend Python, UI React và cả OCR/VLM thật có ví dụ chạy; fake không thay thế tích hợp thật. | Đang triển khai: Python health-check và React skeleton đã kiểm tra CLI/HTTP; còn kiểm tra trực quan frontend, OCR, VLM. |
| R09 | Golden dataset | 5 / S5.1 | Ảnh và ground truth field-level đã rà soát, manifest/version, tập đánh giá tách tập chỉnh cấu hình. | Chưa triển khai |
| R10 | Field-level metrics | 5 / S5.2 | Script chạy lại; test công thức, null và mẫu số 0; báo cáo theo trường. | Chưa triển khai |
| R11 | Error taxonomy | 5 / S5.2 | Mã lỗi và quy tắc phân loại được dùng trong báo cáo; có ví dụ đã kiểm tra. | Chưa triển khai |
| R12 | Model/config version | 3, 5 / S3.1–S3.3, S5.2 | Run metadata có model/config/schema/prompt/dataset version và commit; báo cáo so sánh tái lập. | Chưa triển khai |

## Yêu cầu chất lượng

- Business logic không import SDK OCR/VLM; fake provider chạy được offline, không API key.
- Tách OCR output, extraction gốc, validation result, bản sửa và bản đã xác nhận.
- Validation quan trọng nằm ở backend; frontend hỗ trợ người dùng sửa lỗi.
- Không bịa giá trị thiếu, không coi điểm OCR là xác suất trường đúng, không tự tin hóa điểm VLM.
- Lỗi file hỏng/sai loại/quá giới hạn, OCR/VLM thất bại, timeout, sai schema và export thất bại
  phải được biểu diễn rõ; không trả output giả như thể xử lý thật thành công.
- Không log nội dung tài liệu, trường dữ liệu hoặc secrets. Chỉ log mã lỗi, request/run ID và thời gian.
- Dữ liệu tải lên chỉ lưu tạm nếu cần, dọn sau xử lý; chưa có lưu trữ lâu dài, tài khoản hay cloud.

## Kế hoạch evaluation ban đầu

Chưa có golden dataset, script hay kết quả chất lượng. Giai đoạn 5 dự kiến tạo một bộ nhỏ
khoảng 20–30 tài liệu tổng hợp có biến thể dấu tiếng Việt, bố cục, nhiễu, trường thiếu và
giá trị nhập nhằng. Tách tập dùng chỉnh rule/prompt với tập đánh giá trước khi chạy so sánh;
không đưa ground truth của tập đánh giá vào provider.

Tính exact match sau chuẩn hóa theo trường; công bố chuẩn hóa và support.
Báo cáo riêng null/null để không che độ chính xác trường có dữ liệu. Với PRF:
TP là dự đoán khác null và đúng; giá trị sai khác null tính FP và, nếu gold có giá trị,
tính FN; bỏ sót gold tính FN; null/null không tính TP. Mẫu số 0 trả `null` kèm số đếm,
không tự quy thành 100%. Có thể tổng hợp micro/macro nhưng luôn giữ báo cáo từng trường.

Taxonomy dự kiến: `input_invalid`, `ocr_text`, `layout`, `field_missing`, `field_wrong`,
`normalization`, `schema_invalid`, `business_validation`, `provider_timeout`, `export_error`.
Lưu trường bị ảnh hưởng và bằng chứng, cho phép nhiều nhãn; không suy đoán nguyên nhân OCR
khi chưa kiểm tra OCR output. Chốt định nghĩa và ví dụ ở S5.2 trước khi công bố báo cáo.

Mỗi run cần gắn commit code, dataset version/hash, schema version, OCR engine và model/weights,
VLM model/revision, prompt/config version/hash, tham số generation và thời gian chạy.
Nếu provider bên ngoài không bảo đảm tái lập tuyệt đối, ghi rõ giới hạn và lưu output cho so sánh.
