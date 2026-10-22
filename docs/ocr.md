# OCR tiếng Việt

MVP dùng Tesseract và language pack `vie`. Docker image cài cả runtime
`tesseract-ocr` lẫn `tesseract-ocr-vie`; Python dùng `pytesseract`.

```python
engine = VietnameseOCREngine(prefer="tesseract", tesseract_lang="vie")
result = engine.recognize(image)
```

`OCRResult` chứa text, word/bounding box, engine và mean confidence 0–100 do OCR
runtime cung cấp. `assess_confidence` chia quality high/medium/low; text/identifier
không được ghi vào application log.

Mã nguồn còn adapter PaddleOCR để mở rộng, nhưng dependency này không có trong
image/requirements mặc định và chưa được CI test. Fallback mặc định tắt. Chỉ đặt
`OCR_FALLBACK_ENABLED=true` sau khi đã cài và kiểm thử engine còn lại; nếu engine
cấu hình không khả dụng, `/health` trả `degraded` và `/process` trả lỗi xử lý.

PDF được render bằng PyMuPDF (200 DPI); ảnh được resize, grayscale, tăng tương phản
và khử nhiễu bằng OpenCV trước OCR.
