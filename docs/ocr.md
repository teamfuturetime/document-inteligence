# OCR Tiếng Việt

Module OCR nhận dạng văn bản tiếng Việt từ ảnh tài liệu đã qua tiền xử lý.

## Kiến trúc

```
Ảnh đã tiền xử lý
        │
        ▼
┌───────────────────┐
│  VietnameseOCR    │  ai_service/ocr/engine.py
│  Engine           │  Tesseract (chính) → PaddleOCR (dự phòng)
└─────────┬─────────┘
          │ OCRResult (text + words + confidence)
          ▼
┌───────────────────┐
│  Post-processing  │  ai_service/ocr/postprocess.py
│  - Chuẩn hóa NFC │  - Sửa lỗi OCR phổ biến
│  - Dọn whitespace│  - Sửa dấu tiếng Việt
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Confidence       │  ai_service/ocr/confidence.py
│  Scoring          │  Đánh giá chất lượng → cần rà soát?
└───────────────────┘
```

## Engine

`VietnameseOCREngine` hỗ trợ hai engine:

| Engine | Ưu điểm | Cài đặt |
|--------|---------|---------|
| **Tesseract** (mặc định) | Nhẹ, nhanh, hỗ trợ tiếng Việt qua gói `vie` | `pip install pytesseract` + tesseract-ocr + gói `vie` |
| **PaddleOCR** (dự phòng) | Chính xác hơn với ảnh scan, tự phát hiện góc | `pip install paddleocr` (cần Python ≤ 3.11) |

Cơ chế fallback: nếu engine ưu tiên không khả dụng, tự động chuyển sang engine còn lại.

### Sử dụng

```python
from ai_service.ocr.engine import VietnameseOCREngine

engine = VietnameseOCREngine()
result = engine.recognize(image)   # image: numpy array (BGR)
print(result.text)                 # văn bản nhận dạng
print(result.mean_confidence)      # độ tin cậy trung bình (0-100)
```

## Hậu xử lý

`postprocess_text()` thực hiện theo thứ tự:

1. **Chuẩn hóa Unicode** — chuyển NFD → NFC để đồng nhất dấu tiếng Việt
2. **Sửa lỗi OCR phổ biến** — `å → á`, `ä → ă`, `ë → ê`, `| → l`, ...
3. **Sửa dấu sai vị trí** — `hòa → hoà`, `úy → uý` (theo quy tắc chính tả)
4. **Dọn khoảng trắng** — gộp space, bỏ space trước dấu câu

## Độ tin cậy

`assess_confidence()` phân loại chất lượng:

| Chất lượng | Điều kiện | Hành động |
|------------|-----------|-----------|
| `high` | mean ≥ 80 và ≤ 10% từ thấp | Lưu trực tiếp |
| `medium` | mean ≥ 50 | Lưu, đánh dấu cần kiểm tra |
| `low` | mean < 50 | Chạy lại với engine khác / yêu cầu rà soát thủ công |

`should_reprocess()` quyết định có nên chạy lại OCR với engine dự phòng không.

## Tích hợp pipeline

Trong pipeline xử lý tài liệu (xem `docs/pipeline.md`), OCR nằm sau bước
tiền xử lý ảnh và trước bước trích xuất thông tin:

```
Upload → Validate → Preprocess → OCR → Post-process → Extract → Store
```
