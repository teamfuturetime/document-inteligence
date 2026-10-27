# OCR tiếng Việt

MVP dùng Tesseract và language pack `vie`. Docker image cài cả runtime
`tesseract-ocr` lẫn `tesseract-ocr-vie`; Python dùng `pytesseract`.

```python
engine = VietnameseOCREngine(prefer="tesseract", tesseract_lang="vie")
result = engine.recognize(image)
```

`OCRResult` chứa raw text, word/bounding box, page/block/paragraph/line number,
engine và mean confidence 0–100 do OCR runtime cung cấp. Từ metadata thật này,
pipeline dựng `pages → blocks → lines → cells`; các loại block chỉ được gán khi có
tín hiệu hình học. Block bảng thiếu ô được đánh dấu `needs_review`, không tự điền.
`assess_confidence` chia quality high/medium/low; text/identifier không được ghi vào
application log.

Mã nguồn còn adapter PaddleOCR để mở rộng, nhưng dependency này không có trong
image/requirements mặc định và chưa được CI test. Fallback mặc định tắt. Chỉ đặt
`OCR_FALLBACK_ENABLED=true` sau khi đã cài và kiểm thử engine còn lại; nếu engine
cấu hình không khả dụng, `/health` trả `degraded` và `/process` trả lỗi xử lý.

PDF được render bằng PyMuPDF ở 250 DPI (cấu hình 150–300). Ảnh được deskew có giới
hạn và tạo tối đa ba candidate: grayscale an toàn, CLAHE + denoise/sharpen nhẹ, và
adaptive threshold. Tesseract chạy `--oem 3 --psm 3` trước; chỉ thử thêm PSM/candidate
khi confidence đo được thấp, tối đa `OCR_MAX_ATTEMPTS`. Candidate được chọn bằng
confidence, tỷ lệ từ confidence thấp và coverage ký tự—không bằng suy đoán nội dung.

Mặc định dùng `vie`. Benchmark tổng hợp hiện tại cho thấy `vie+eng` không tốt hơn
trên bộ mẫu, vì vậy không bật song ngữ mặc định. Xem [đánh giá OCR](evaluation.md).

Raw OCR không qua phép thay chữ/số. Bản cleaned chỉ chuẩn hóa Unicode, control
character và khoảng trắng; giữ nguyên chữ hoa, số tiền, ngày, MST và line boundary.
