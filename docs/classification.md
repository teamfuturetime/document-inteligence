# Phân Loại Tài Liệu

Module phân loại loại tài liệu tiếng Việt (CCCD, CMND, hợp đồng, đơn từ...) từ văn bản OCR.

## Kiến trúc

```
Văn bản OCR đã hậu xử lý
        │
        ▼
┌──────────────────────────┐
│  DocumentClassifier      │  ai_service/classification/engine.py
│  Keyword + regex scoring │  Khớp từ khóa (đã chuẩn hóa bỏ dấu)
└────────────┬─────────────┘
             │ ClassificationResult
             ▼
┌──────────────────────────┐
│  DocumentTypeDetector    │  ai_service/classification/rules.py
│  Pattern đặc thù từng loại│  Kết hợp keyword + regex đặc thù
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  Confidence Scoring      │  ai_service/classification/confidence.py
│  Phát hiện mơ hồ         │  Hai loại gần điểm → cần rà soát
└──────────────────────────┘
```

## Engine từ khóa

`DocumentClassifier` khớp từ khóa trên văn bản đã **chuẩn hóa bỏ dấu**
(NFD + loại combining character), nên `CĂN CUỚC` và `Căn cước` đều khớp.

```python
from ai_service.classification.engine import build_vietnamese_classifier

classifier = build_vietnamese_classifier()
result = classifier.classify(ocr_text)
result.document_type  # "cccd" | "cmnd" | ...
result.confidence     # 0-99 (% tủ số lượng từ khóa khớp)
```

## Detector quy tắc

`DocumentTypeDetector` kết hợp:
- **Từ khóa** từ `DocumentClassifier` (trọng số 0.5)
- **Pattern đặc thù** từng loại tài liệu (trọng số 1.0 mỗi pattern)

Pattern đặc thù giúp phân biệt chính xác, ví dụ CCCD thường có
`Số: 12 chữ số`, `Quê quán`, `Nơi thường trú`, `Có giá trị đến`.

```python
from ai_service.classification.rules import DocumentTypeDetector

detector = DocumentTypeDetector()
result = detector.detect(text)
source = result.source  # "rule"
```

## Các loại tài liệu hỗ trợ

| Loại | Từ khóa chính | Pattern đặc thù |
|------|---------------|-----------------|
| `cccd` | căn cước, cccd | Số 12 chữ số, Quốc hiệu, Ngày sinh |
| `cmnd` | chứng minh nhân dân, cmnd | Số 9 chữ số, Dân tộc, Tôn giáo |
| `hop_dong_lao_dong` | hợp đồng lao động, hđld | Bên A, Bên B, Thời hạn, Tiền lương |
| `don_xin_viec` | đơn xin việc, kính gửi | Tôi viết đơn này, Người làm đơn |
| `ho_khau` | hộ khẩu, sổ hộ khẩu | Chủ hộ, Quan hệ với chủ hộ |

## Độ tin cậy

`assess_classification()` trả về báo cáo chất lượng:

| Chất lượng | Điều kiện |
|------------|-----------|
| `high` | Độ tin cậy ≥ 80 và không mơ hồ |
| `medium` | Độ tin cậy ≥ 50 |
| `low` | < 50 hoặc không xác định |

Báo cáo cũng phát hiện **mơ hồ** (hai loại có điểm chênh < 30%) — những
tài liệu này được đánh dấu cần rà soát thủ công trước khi xử lý tiếp.

## Tích hợp pipeline

Trong pipeline (xem `docs/pipeline.md`), phân loại chạy ngay sau OCR:

```
Upload → Validate → Preprocess → OCR → Classify → Extract → Store
```

Loại tài liệu xác định được dùng để chọn bộ pattern trích xuất phù hợp
(xem `docs/extraction.md`), giúp tăng độ chính xác trích xuất từng loại giấy tờ.