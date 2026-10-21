# OCR local S3.2

S3.2 đã chạy nhận dạng thật trên ảnh tổng hợp, ngày 21/10/2026, Windows/Python 3.13.7.
Đây là OCR text/token, chưa phải extraction năm trường hóa đơn, review hoặc export.
Quyết định chọn engine: [ADR 0001](adr/0001-local-tesseract-ocr.md).

## Môi trường và nguồn

- Engine đang kiểm tra: `tesseract v5.5.0.20241111`, OEM 1 (LSTM), PSM 6, DPI 300,
  ngôn ngữ `vie`. Không cần API key, GPU, dịch vụ trả phí hoặc mạng khi chạy.
- Model `vie.traineddata`: SHA-256
  `79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1` (531275 bytes).
  Đã so hash với [file chính thức tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast/blob/main/vie.traineddata)
  ngày 21/10/2026; metadata mỗi kết quả ghi hash file thực sự đang dùng.
- Engine và tessdata_fast có giấy phép Apache-2.0:
  [Tesseract](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE),
  [model](https://github.com/tesseract-ocr/tessdata_fast/blob/main/LICENSE).
  Không đưa executable, DLL hoặc model vào repository.
- Pillow **13.0.0** thêm vào dependency runtime để giải mã PNG/JPEG, xử lý EXIF và
  tạo ảnh smoke; giấy phép [MIT-CMU](https://pillow.readthedocs.io/en/stable/about.html#license).
  Không cần pytesseract, SDK AI hoặc framework mới.

## Chạy lại

Cài dependency theo README. Máy này đã có Tesseract ở
`E:\Program Files\Tesseract-OCR\tesseract.exe`, model ở thư mục `tessdata` bên cạnh.
Không thay đổi bản cài hệ thống trong S3.2. Máy khác cần tự cài engine và model `vie`
theo [hướng dẫn chính thức](https://tesseract-ocr.github.io/tessdoc/Installation.html).

Chạy từ thư mục gốc repository trong PowerShell:

```powershell
tesseract --version
tesseract --list-langs
Push-Location backend
..\.venv\Scripts\python.exe -m app.ocr_cli ../data/ocr-smoke/invoice_vi.png
Pop-Location
```

CLI ghi JSON Unicode ra stdout theo yêu cầu, lỗi chỉ ghi code ra stderr và exit 1.
Đổi ảnh sang `invoice_vi.jpg` hoặc `blank.png` để thử. Nếu executable không ở PATH,
thêm `--tesseract 'đường dẫn/tesseract.exe'`; nếu model không nằm cạnh executable,
thêm `--tessdata-dir 'đường dẫn/tessdata'`. `--timeout` mặc định 30 giây mỗi tiến trình.
Đường dẫn tương đối được tính theo thư mục đang chạy. Không tự tải model hoặc fallback fake.

Trong code backend: tạo `DocumentInput`, gọi `TesseractOCRProvider(...).recognize(document)`;
caller bắt `ProviderError` theo code hiện có. `OCRProvider` là Protocol OCR-only;
không giả làm `ExtractionProvider` của S3.1 hoặc tạo raw_values hóa đơn khi chưa extraction.

## Contract và xử lý ảnh

`OCRResult` có document ID, SHA-256 input và PNG đã xử lý, kích thước ảnh hiển thị,
`raw_text`, `raw_tsv`, words (text/page/bbox/native_confidence), metadata và warnings.
Metadata chứa identity/version/config của adapter, engine version, model hash,
toàn bộ tham số xử lý và config hash, Pillow version, thang score gốc.

Pillow kiểm tra format thực khớp MIME PNG/JPEG, từ chối ảnh hỏng, nhiều frame và
ảnh vượt guard nội bộ 10 MiB hoặc 20 triệu pixel. Đây là guard tài nguyên adapter,
chưa phải chính sách upload API. EXIF được áp dụng trước OCR, alpha được ghép trên
nền trắng rồi chuyển RGB; không deskew, resize hoặc tự sửa nội dung chữ.
Toạ độ pixel tính từ góc trên trái của ảnh đã áp dụng EXIF, có width/height và được
kiểm tra cận. Nếu review UI được triển khai sau, phải hiển thị cùng hệ toạ độ này.

Text/TSV được giải mã UTF-8, giữ nguyên xuống dòng nguồn, không normalize hoặc sửa dấu.
TSV sai header/row/page/geometry/score bị từ chối. Word score giữ thang Tesseract
0–100, `-1` biểu diễn unavailable thành null; TSV thô vẫn giữ số gốc. Không chia 100,
không coi đó là confidence extraction hoặc xác suất đúng trường dữ liệu.

Adapter gọi subprocess bằng danh sách argv, shell=False; version query và OCR có
timeout riêng. subprocess.run giết và chờ tiến trình con khi hết hạn; không phải
deadline tổng bao gồm decode/hash và chưa có cơ chế quản lý cây tiến trình tổng quát.
Text và TSV từ cùng lần nhận dạng, file tạm được dọn kể cả lỗi/timeout.
Không log tài liệu hoặc đưa stderr engine vào lỗi công khai.

| Code / kết quả | Ý nghĩa |
| --- | --- |
| `invalid_document` | Sai input, MIME/format, ảnh hỏng/nhiều frame hoặc vượt guard ảnh. |
| `provider_unavailable` | Không tìm được executable hoặc file model không đọc được. |
| `provider_timeout` | Tiến trình version/OCR vượt timeout. |
| `provider_failed` | Exit khác 0, output thiếu/hỏng/sai UTF-8 hoặc TSV không hợp lệ. |
| Thành công, warning `no_text` | Engine chạy được nhưng text trống, words rỗng; không phải hóa đơn hợp lệ. |

## Mẫu và kết quả thực tế

`data/ocr-smoke/` có hai ảnh cùng hóa đơn tổng hợp (PNG/JPEG, 1600×1050) và một PNG
trắng (800×400). Manifest ghi ID, nguồn/quyền dùng, locale, kích thước/hash và text
để đối chiếu. Nội dung/layout gốc và ảnh mẫu được dành theo CC0-1.0; font Arial của
máy chỉ dùng render, không phân phối font. Chưa phải golden dataset hoặc tập đánh giá.

Tạo lại (có thể đổi bytes/hash nếu font/Pillow khác; review manifest khi regenerate):

```powershell
.\.venv\Scripts\python.exe data/ocr-smoke/generate.py --font C:/Windows/Fonts/arial.ttf
```

Đã xem trực quan PNG tạo ra. OCR thật đọc được tiêu đề, `Cửa hàng Mây Việt`,
`HD-0000123`, `03/04/2026` và `125.000 VND` trên cả PNG/JPEG. Ảnh trắng trả no_text;
ảnh JPEG xoay có EXIF được đưa về đúng kích thước/chiều trước nhận dạng.
So sánh thử cùng ảnh PNG, `vie+eng` làm mất nhiều dấu ở nhãn; chọn `vie` cho mẫu
tiếng Việt này. `vie` vẫn đọc nhầm `TỔNG` thành `TỎNG`, `GIẢ LẬP` thành `GIÁ LẬP`.
Không sửa các lỗi đó trong output hoặc tuyên bố OCR hoàn hảo. Chưa có metric, ngưỡng
confidence hoặc bằng chứng chất lượng trên ảnh thực tế/ảnh khó.

Xem [testing](testing.md) cho lệnh và kết quả thật. Task kế tiếp: S3.3 — VLM thật
và chính sách confidence; chưa triển khai trong S3.2.
