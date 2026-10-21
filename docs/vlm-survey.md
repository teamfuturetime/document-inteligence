# S3.3.1 — Khảo sát VLM cho sales_invoice 1.0.0

Ngày kiểm tra: **21/10/2026**, Asia/Saigon. Trạng thái: khảo sát và thiết kế,
**chưa tải/chạy VLM, chưa benchmark, chưa chọn provider production**.
Không có kết quả accuracy, latency, RAM peak hoặc confidence thực nghiệm trong tài liệu này.

## 1. Trạng thái repository đã xác minh

- Branch `tuannguyen`, HEAD `7a28be309eb3da380795a46d7c738105351dafbf`, working tree
  sạch trước sửa. Remote fetch/push: `https://github.com/teamfuturetime/document-inteligence.git`.
  Refs local báo ahead 2; không fetch nên không khẳng định trạng thái GitHub hiện tại.
- Đã đối chiếu README, roadmap, requirements, architecture, testing, OCR, handoff,
  ADR 0001 và code S3.1–S3.2. S3.2 có OCR thật; không có VLM adapter hoặc benchmark runner.
- `ExtractionProvider.extract(DocumentInput) -> ProviderOutput` nhận ảnh bytes,
  trả năm raw_values, locale, uncertain_fields, metadata/evidence và OCR text nullable.
  `run_pipeline` revalidate rồi gọi normalization/business validation S2.2.
- `OCRProvider.recognize` và `OCRResult` độc lập, có text/TSV, word bbox/native score,
  kích thước ảnh sau EXIF và engine/model/config hash. Pipeline S3.1 chưa gọi OCR.
- Canonical `InvoiceValues`/`FinalInvoiceValues`, schema `sales_invoice` **1.0.0**
  giữ nguyên. Schema validity không chứng minh dữ liệu khớp ảnh hoặc đã được duyệt.

## 2. Phần cứng thực tế và giới hạn thông tin

Truy vấn CIM ban đầu bị Access denied trong sandbox; chạy lại read-only với quyền
được cấp đã lấy được các số dưới đây. Không cài công cụ hoặc driver mới.

| Thành phần | Kết quả đã kiểm chứng |
| --- | --- |
| Máy / OS | Lenovo 21LE, Microsoft Windows 11 Home, 64-bit. |
| CPU | Intel Core Ultra 5 125H; CIM báo 14 cores, 18 logical processors. |
| RAM vật lý | 33,820,106,752 bytes, khoảng 31.5 GiB; RAM trống tại snapshot khoảng 15.7 GiB, có thể thay đổi. |
| GPU được CIM liệt kê | Một `Intel(R) Arc(TM) Graphics`, driver `32.0.101.8243`. |
| VRAM | **Chưa xác định dedicated VRAM/shared-memory budget**. CIM AdapterRAM=2,147,479,552 bytes không đủ chứng minh VRAM khả dụng cho VLM. |
| NVIDIA/CUDA | Không tìm thấy nvidia-smi trên PATH; không suy ra tuyệt đối không có NVIDIA hoặc CUDA. Chưa kiểm tra backend tăng tốc Intel/SYCL. |
| Ổ repo E: | Snapshot còn 134,300,295,168 bytes, khoảng 125.1 GiB; không phải RAM/VRAM. |

Lệnh đọc: `Get-CimInstance Win32_ComputerSystem`, `Win32_Processor`,
`Win32_VideoController`, `Win32_OperatingSystem`; `Get-Command nvidia-smi`;
`Get-PSDrive -PSProvider FileSystem`. Xuất từng nhóm qua ConvertTo-Json để tránh
PowerShell tự ẩn cột của các loại object khác nhau. Không ghi serial/user identity.

**Suy luận kỹ thuật:** dùng CPU làm baseline local; chưa cam kết model vừa GPU.
Với mô hình danh nghĩa 4B, phép tính thô 4e9 × 2 bytes ≈ 8 GB chỉ là phần trọng số
16-bit; KV cache, vision, activations, runtime và OS cần thêm bộ nhớ. Không phải
mức RAM/VRAM tối thiểu đã đo. Quantization giảm trọng số nhưng có thể đổi chất lượng.

## 3. So sánh ứng viên từ nguồn chính thức

Đây là shortlist thực dụng, không tuyên bố các model mới nhất hoặc tốt nhất.
Thông tin model card là tuyên bố của nhà phát hành, chưa là kết quả trên dữ liệu dự án.

| Ứng viên / nguồn | Tiếng Việt và biểu mẫu | Local/API, tài nguyên/chi phí | JSON/schema | Evidence và rủi ro |
| --- | --- | --- | --- | --- |
| [Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) | Card nêu OCR 32 ngôn ngữ, cấu trúc tài liệu và spatial grounding; chưa xác minh cam kết riêng cho hóa đơn tiếng Việt. | Local; có [GGUF chính thức](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF). CPU là hướng thử trên máy này; peak RAM/latency chưa đo. | Prompt JSON không tự bảo đảm schema. Runtime có thể thêm constrained decoding; vẫn phải validate. | Có thể đề xuất vùng/quote, phải đối chiếu nguồn. CPU có thể chậm, quantization/hallucination có thể làm sai dấu hoặc số. |
| [InternVL3_5-4B](https://huggingface.co/OpenGVLab/InternVL3_5-4B) | Card multilingual, có nhóm đánh giá document/OCR và grounding; chưa có bằng chứng invoice tiếng Việt đã xác minh. | Local; ví dụ chính thức dùng Transformers/CUDA và custom code, không chứng minh tương thích Arc hoặc tốc độ CPU máy này. RAM/VRAM thực tế chưa đo. | Không thấy bảo đảm strict JSON Schema ở model card; cần parser và kiểm tra backend. | Có grounding nhưng chưa là evidence field đã kiểm chứng. Có thêm rủi ro runtime/custom code và latency. |
| [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), ID `gemini-3.5-flash-lite` | Trang chính thức nêu multimodal/document parsing; chưa có số đo invoice tiếng Việt. Ngôn ngữ giao diện tài liệu không phải bằng chứng model hỗ trợ tiếng Việt tốt. | API, không cần giữ model trên máy; phụ thuộc mạng/quota. Có giá token bên dưới; chưa xác minh quyền truy cập tài khoản hoặc gọi thử. | [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) hỗ trợ subset JSON Schema; cần validate semantic values. | Chọn OCR IDs/quote hoặc đề xuất bbox; không mặc định box đúng. Mạng, refusal, timeout, thay đổi model và hallucination cần ghi riêng. |

Các model đều có thể được thử với ảnh, text OCR hoặc cả hai nếu runtime hỗ trợ.
Chạy text-only cùng VLM là đối chứng phụ thuộc OCR, không chứng minh năng lực đọc ảnh.
Không lấy DocVQA/multilingual score do hãng công bố làm accuracy trên sales_invoice.
[Model card Gemini của DeepMind](https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/)
cũng ghi giới hạn hallucination và khả năng chậm/timeout; không có bảo đảm invoice
tiếng Việt hoặc SLA cho luồng dự án.

### License và quyền dùng

- Qwen model card gốc và GGUF ghi **Apache-2.0**; [license repository Qwen](https://raw.githubusercontent.com/QwenLM/Qwen3-VL/main/LICENSE)
  cũng là Apache-2.0. Khi lấy bản cụ thể phải pin revision, giữ license/notice và kiểm tra dependency/runtime riêng.
- InternVL checkpoint card ghi **Apache-2.0**, trong khi [code repository](https://raw.githubusercontent.com/OpenGVLab/InternVL/main/LICENSE)
  là **MIT**. Không gộp license code với weights. Card có trust_remote_code; nếu chọn
  phải pin/review code. Không xác minh được file LICENSE riêng của checkpoint qua URL
  đã thử; cần lưu card/license tại revision được chọn trước khi tải/redistribute.
- Gemini là dịch vụ theo [Gemini API Terms](https://ai.google.dev/gemini-api/terms),
  không phải weights Apache để tải local. Phải kiểm tra access/quota/điều khoản tài khoản;
  unpaid service có chính sách dùng input/output để cải thiện sản phẩm, paid khác.
  Không gửi ảnh dù tổng hợp trong phiên khảo sát này, không đọc secret/API key.

### JSON, resource và giá: điều gì được xác minh, điều gì chưa

- [Danh sách file GGUF của Qwen](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/tree/main)
  hiển thị LLM Q4_K_M khoảng **2.5 GB** và vision projector F16 khoảng **836 MB**
  (hoặc Q8_0 khoảng 454 MB). Đây là kích thước file, không phải RAM peak. Phương án
  thử: Q4_K_M + mmproj F16, khoảng 3.34 GB weights, chưa tải. Không tải toàn repo 16.1 GB.
- [Card GGUF](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF) nêu CPU/Intel SYCL;
  không suy ra build/driver máy này chạy tốt. [llama.cpp multimodal](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)
  và [grammar](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)
  là tài liệu runtime cần pin/test: có JSON-schema-to-grammar subset, không kiểm tra
  ngày lịch hoặc tính đúng của giá trị. Khả năng kết hợp grammar + vision phải kiểm tra trên build thực.
- InternVL: chưa có minimum VRAM cho đúng 4B checkpoint được xác minh; ví dụ load
  trong card dùng 8B, không lấy yêu cầu ví dụ đó làm minimum của 4B. Chưa chọn runtime CPU cho ứng viên này.
- [Bảng giá Gemini](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite)
  tại ngày khảo sát: standard input text/image **USD 0.30 / 1M token**, output gồm
  thinking **USD 2.50 / 1M token**. Chi phí giả định `0.30*Tin/1e6 + 2.50*Tout/1e6`,
  không phải báo giá mỗi hóa đơn. Tin gồm token ảnh/OCR/prompt thực tế; retry/think/caching
  có thể đổi chi phí. Free tier có hạn mức, không mặc định tài khoản truy cập được.
- Không chọn Gemini 2.5 Flash làm mặc định mới: [trang model](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash)
  hiện thông báo giới hạn truy cập 2.5 cho người đã dùng trước đó. Cần kiểm tra lại
  availability và giá khi thực hiện; không dùng thông tin giá cũ như bảo đảm tương lai.

## 4. Khuyến nghị có điều kiện

**Ưu tiên benchmark local Qwen3-VL-4B-Instruct-GGUF Q4_K_M + mmproj F16**, CPU,
batch 1. Lý do do dự án tự đánh giá: có weights quantized chính thức, tránh mặc định
phụ thuộc CUDA/API, có thể giữ ảnh local; có đường constrained JSON. Không kết luận
Qwen tốt hơn InternVL/Gemini trước khi đo. Không khuyến nghị cài nhiều runtime cùng lúc.

Budget thử đề xuất: context 4096 nếu đủ token ảnh/prompt, max output 768, seed cố định,
greedy/no sampling khi runtime cho phép; ghi toàn bộ tham số, không cắt input âm thầm.
Giới hạn một run 120 giây và mục tiêu peak RAM process 12 GiB là **guard đề xuất**,
không phải số đo hoặc SLA. Nếu context không đủ hoặc vượt guard thì ghi lỗi/không phù hợp,
không đổi cấu hình giữa benchmark rồi gộp kết quả. Intel GPU acceleration chỉ là thử nghiệm sau CPU baseline.

Gemini là đối chứng tùy chọn nếu người dùng cho phép gửi dữ liệu và chốt ngân sách;
InternVL là đối chứng local sau khi có runtime/phần cứng phù hợp. Việc đọc tài liệu
không cấp phép tự tải model/runtime hoặc gọi API; task hiện tại dừng ở đề xuất.

## 5. Benchmark nhỏ, có thể tái lập — chưa chạy

### Dữ liệu và nhãn tham chiếu

Giữ nguyên [manifest ocr-smoke-1](../data/ocr-smoke/manifest.json). Đã kiểm tra hash
ba file khớp manifest; hai ảnh invoice cùng nội dung, chỉ khác PNG/JPEG, cộng một blank.
Đó là **một hóa đơn độc lập + một negative**, không phải ba hóa đơn hoặc golden dataset.
Không đưa expected_text/labels/đường dẫn có giá trị đáp án vào prompt hay provider.

Nhãn canonical đề xuất cho cả hai ảnh invoice, đối chiếu text generator/manifest:

```json
{
  "invoice_number": "HD-0000123",
  "invoice_date": "2026-04-03",
  "seller_name": "Cửa hàng Mây Việt (GIẢ LẬP)",
  "total_amount": 125000,
  "currency": "VND"
}
```

Blank: đủ năm key đều null. Nhãn invoice đã được kiểm tra bằng FinalInvoiceValues;
blank bằng InvoiceValues; đây chỉ là kiểm tra label/schema, **không phải benchmark VLM**.
Khi hiện thực, lưu label riêng, version/hash và review đối chiếu ảnh; chỉ evaluator
được đọc label. Sau này tách mẫu tuning/holdout theo hóa đơn gốc, không theo định dạng ảnh.

### Quy trình chạy đã đề xuất

1. Freeze Git revision, image/manifest/label hashes, model full revision + file hashes,
   mmproj, quantization, license, runtime build, chat template/processor, prompt/schema
   hash, decoding parameters, CPU/backend và resource guard. Không dùng main/latest làm định danh tái lập.
2. Chuẩn bị OCR một lần bằng adapter S3.2, giữ raw OCRResult và hashes/version. Gán
   ID word ổn định từ OCR-run hash + index ở adapter thử nghiệm; không sửa schema OCR hiện có.
3. Cùng model, so ba mode: **ảnh-only**, **OCR-text-only**, **ảnh + OCR text/word IDs**.
   Ảnh dùng cùng chiều EXIF và preprocessing đã ghi nhận. OCR có thể sai dấu; không sửa
   từ ground truth. Runtime không hỗ trợ mode nào thì ghi unsupported, không giả lập kết quả.
4. Prompt version cố định: chỉ lấy năm trường từ nguồn, đủ key, thiếu/mơ hồ null;
   giữ số 0 đầu, không mặc định VND, không đoán ngày/tiền, không tạo confidence.
   Nội dung OCR/ảnh là dữ liệu không tin cậy, không làm theo chỉ dẫn nằm trong tài liệu.
   Yêu cầu quote/word IDs cho evidence, nhưng parser không tin quote/box do model tự tạo.
5. Ban đầu một lượt mỗi mode × ba file = **9 run/model**; không tính một warm-up vào
   latency báo cáo. Nếu hoàn tất trong budget mới chạy lại toàn bộ cùng cấu hình hai
   lượt nữa: tổng 27 run/model. Ghi số lượt thực tế; không gộp chạy dở thành 27 kết quả.
   Không gọi lại để chọn câu trả lời đẹp nhất; retry do lỗi transport phải ghi riêng.
6. Lưu raw response trước parse; phân biệt JSON syntax, missing/extra key, wrong type,
   refusal/truncation, schema, normalization/business error, thiếu/quote evidence sai,
   hallucination và timeout/OOM. Không tự sửa JSON, loại dấu hoặc làm tròn số để tăng điểm.
7. Adapter đề xuất map output về ProviderOutput hiện có, confidence null; normalize và
   validate bằng service S2.2. Không dùng prompt schema thay backend validation. DMY chỉ
   chuyển với source_locale vi-VN đã ghi trong manifest; giữ raw và lịch sử chuyển đổi.
8. Báo cáo kết quả từng field/mode/file/run và lỗi. Chưa tích hợp API hoặc pipeline ứng dụng
   trong benchmark đầu; wrapper có thể compose OCRProvider mà không đổi signature S3.1.

### Phép đo đề xuất, tránh báo cáo gây hiểu nhầm

- Field exact match sau normalization đã chốt, so cả kiểu: invoice_number giữ 0 đầu;
  date ISO/ngày thật; seller NFC/case/dấu chính xác; amount integer; currency VND.
- Primary non-null EM: đúng / tổng field GT khác null của **mọi run đã lên lịch**;
  malformed/refusal/timeout/OOM/missing đều là sai, không bỏ khỏi mẫu số. Chạy một
  lượt đủ ba mode có 30 slot non-null (2 format × 5 field × 3 mode); không phải 30 mẫu độc lập.
- Báo EM từng field và mode; all-five-correct cho positive, JSON parse/schema/validation
  success rates trên mọi run. Diagnostics trên run thành công phải ghi mẫu số riêng.
- Blank: false positive là dự đoán field khác null; báo số field bịa và tỷ lệ all-null
  riêng. Null/null không được cộng để làm tăng non-null EM. Failure trên blank không
  được tính là abstention đúng; phải báo availability/error và blank-pass riêng.
- Evidence coverage/quote-ID validity báo riêng; đúng chuỗi chưa chứng minh đúng vùng
  ảnh. Tách raw candidate EM khỏi số field được chấp nhận sau evidence/uncertainty gate.
  Raw candidate EM là diagnostic từ bản normalize riêng trước gate, không phải giá
  trị đã được chấp nhận hoặc sửa lại kết quả run_pipeline để tăng điểm.
  Requirements yêu cầu candidate có evidence; không đẩy field thiếu nguồn thành bản được tin cậy.
- Latency: tách cold load, OCR, model inference, parse/validation; lưu wall time và peak
  process RAM, GPU memory nếu đo được. Với ít mẫu chỉ báo từng run/median và số mẫu,
  không công bố p95 hoặc suy diễn SLA. API ghi usage tokens, giá tại thời điểm chạy,
  phí thực khi có; không bịa số token/chi phí hoặc độ tái lập tuyệt đối.
- Smoke set không đủ calibration, xếp hạng tổng quát hoặc precision/recall đáng tin cậy.
  Các mẫu missing/uncertain/date sai/tiền mơ hồ khác sẽ cần bộ tổng hợp riêng có version;
  chưa tạo thêm dữ liệu hoặc biến chúng thành benchmark đã chạy trong S3.3.1.

## 6. Provenance và confidence đề xuất

| Loại thông tin | Nơi lưu / ý nghĩa | Không được suy ra |
| --- | --- | --- |
| OCR native score | OCRResult.words, thang Tesseract 0–100; -1 unavailable thành null, TSV thô giữ nguyên. | Không phải xác suất đúng field; không chia 100 rồi gắn vào FieldConfidence. |
| Model tự báo score | Chỉ giữ trong raw response/sidecar nghiên cứu nếu model tự sinh; prompt chính không yêu cầu. | Không map sang source calibrated_extraction hoặc ocr_aggregation. |
| Confidence hiệu chuẩn | Chỉ thêm sau calibration trên tập độc lập đủ lớn, có method/calibration version, evidence IDs và đánh giá reliability/coverage. | Hiện chưa có; FieldMetadata.confidence luôn null, không đặt 0 hay 1 thay cho chưa biết. |
| Accuracy benchmark | Report aggregate theo field/mode/dataset/version, có mẫu số và failures. | Không dùng một accuracy chung làm confidence cho từng hóa đơn. |

Provider identity name/implementation/config version ở S3.1 không đủ provenance VLM
chi tiết. Thiết kế **sidecar run record** cho benchmark, chưa thêm key vào model hiện có:
Git revision, schema/normalization/pipeline version; model ID/full revision/weight &
mmproj hashes/quantization; runtime/Pillow/processor/chat-template versions; prompt và
JSON schema hash; decoding/seed/context/image preprocessing; input & processed hash,
OCR run/hash; timestamp, raw response hash, error/status, latency/memory và token usage nullable.
API thêm requested model và resolved version nếu được trả; không có thì null, không bịa.

Evidence đề xuất: VLM chọn OCR word IDs; adapter tra text/page/bbox từ OCRResult đã lưu,
kiểm tra ID tồn tại, không trùng, quote khớp, bbox trong ảnh sau EXIF. Không tin text/bbox
do VLM tự báo là chứng cứ đã có. Cùng quote có thể chỉ nhầm vị trí nên vẫn cần review.
Image-only hoặc OCR sai nhưng model đọc được ảnh: giữ quote/box model đề xuất trong
sidecar là **chưa xác minh**. Không chế OCR evidence để lấp khoảng trống; dùng evidence
rỗng, confidence null, uncertain và canonical null khi chưa đủ nguồn theo requirements.

Tài liệu [Gemini image understanding](https://ai.google.dev/gemini-api/docs/image-understanding#object-detection)
có ví dụ bbox chuẩn hóa 0–1000; không sao chép trực tiếp sang bbox pixel của dự án
hoặc coi object detection là invoice-field grounding. Muốn dùng phải kiểm tra model,
đổi hệ toạ độ/resize/EXIF có version và kiểm chứng crop/source. Không triển khai ở đây.
User sửa/duyệt không biến score thành 1.0 và không chuyển confidence gốc sang giá trị sửa.

## 7. Task triển khai tiếp theo và tiêu chí nghiệm thu

**S3.3.2 — Benchmark runner local cho Qwen3-VL GGUF và parser/evidence adapter**,
độc lập API/UI. Trước khi tải/chạy, cần được giao task kèm chấp thuận runtime/model
và dung lượng khoảng 3.34 GB weights + runtime; kiểm tra license và pin revision.
Đây là điều kiện cho task sau, không phải yêu cầu phê duyệt trong phiên khảo sát này.

Tiêu chí:

1. Runner CLI batch 1, cấu hình/prompt/version rõ ràng; labels evaluator-only và có
   test chống đọc label trong provider. Không sửa sales_invoice 1.0.0 hoặc S3.1/S3.2.
2. Unit test offline cho parse JSON sai/extra/missing/types/null/uncertainty, số 0 đầu,
   schema/normalization/business errors, evidence ID giả và confidence luôn null.
3. Sau khi môi trường được cho phép: ít nhất một inference thật từ ảnh; hoàn tất
   9 run ban đầu hoặc báo chính xác run thất bại/không thể chạy. Ba mode và negative
   có report từng field; không yêu cầu điểm chất lượng tùy tiện để đánh dấu code chạy được.
4. Có timeout/cancellation thực, guard RAM/context và lưu failure/OOM/refusal, không
   fallback fake hoặc che lỗi bằng retry. Báo raw EM và evidence-gated coverage riêng.
5. Giữ raw response/provenance đã loại secret; CLI không tự gọi API ngoài. Chạy backend
   suite phù hợp, diff check, review rồi làm Git đúng yêu cầu của task được giao.
6. Dùng kết quả để quyết định có tích hợp provider vào pipeline ứng dụng ở bước sau;
   S3.3 umbrella chưa hoàn thành chỉ nhờ khảo sát hoặc smoke benchmark.

## 8. Xác minh trong S3.3.1 và vấn đề còn mở

Đã kiểm tra Git/phần cứng, đọc nguồn chính thức (links cạnh từng nhận định), kiểm tra
manifest hashes và reference labels bằng canonical models hiện có. Chỉ sửa tài liệu;
không chạy lại backend suite hoặc dùng số 463 từ S3.2 như kết quả test mới của task này.
Không stage/commit/push theo yêu cầu. Kiểm tra whitespace/liên kết/JSON minh họa và
`git diff --check` thực hiện khi review cuối.

Còn thiếu: dedicated/shared GPU budget và backend Arc thực tế; RAM/latency/model
quality; runtime build và revision chính xác để triển khai; quyền API/ngân sách nếu
chọn API; review labels/crop độc lập khi tạo benchmark; dữ liệu calibration đủ lớn.
Các trang main/pricing có thể đổi sau ngày khảo sát; phải xác minh lại trước khi chạy.

## Cập nhật phạm vi S3.3.2a theo prompt tiếp theo

Kế hoạch S3.3.2 trong phần 7 được tách thành **S3.3.2a offline** và **S3.3.2b inference thật**.
S3.3.2a hiện có runner/parser/evidence lookup và fixture diagnostics; không đáp ứng hoặc
tuyên bố đã làm tiêu chí inference thật/resource guard VLM trong phần 7. Xem
[benchmark offline](benchmark-offline.md) cho contract/metrics/test, roadmap cho bước b.
Toàn bộ khảo sát và các giới hạn nguồn/phần cứng ở trên được giữ nguyên.
