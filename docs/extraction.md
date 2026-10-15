# Trích Xuất Dữ Liệu

Module trích xuất các trường dữ liệu có cấu trúc từ văn bản OCR của biểu mẫu tiếng Việt.

## Kiến trúc

```
Văn bản OCR đã hậu xử lý
        │
        ▼
┌──────────────────────┐
│  ExtractionEngine    │  ai_service/extraction/engine.py
│  FieldPattern list   │  Regex pattern → trường dữ liệu
└─────────┬────────────┘
          │ ExtractionResult (fields)
          ▼
┌──────────────────────┐
│  Rule-based (VN)     │  ai_service/extraction/rules.py
│  Biểu mẫu tiếng Việt│  CCCD, Họ tên, Ngày sinh, ...
└─────────┬────────────┘
          ▼
┌──────────────────────┐
│  Confidence Scoring  │  ai_service/extraction/confidence.py
│  Hợp lệ hóa dữ liệu │  Kiểm tra CCCD, ngày, SĐT, email
└──────────────────────┘
```

## Engine

`ExtractionEngine` nhận danh sách `FieldPattern` — mỗi pattern là một regex
với tên trường, độ tin cậy mặc định, và đánh dấu bắt buộc.

```python
from ai_service.extraction.engine import ExtractionEngine, FieldPattern
import re

engine = ExtractionEngine([
    FieldPattern("cccd", re.compile(r"Số:\s*([0-9]{9,12})"), confidence=95.0),
])
result = engine.extract(ocr_text)
result.to_dict()  # {"cccd": "079201012345"}
```

## Bộ quy tắc tiếng Việt

`build_vietnamese_form_engine()` cung cấp sẵn các pattern cho giấy tờ phổ biến:

| Trường | Pattern | Ví dụ |
|--------|---------|-------|
| `cccd` | 9-12 chữ số sau nhãn "Số" | `079201012345` |
| `full_name` | sau "Họ và tên" | `Nguyễn Văn Nam` |
| `birth_date` | dd/mm/yyyy sau "Ngày sinh" | `15/08/1990` |
| `gender` | Nam/Nữ | `Nam` |
| `hometown` | sau "Quê quán" | `Hà Nội` |
| `address` | sau "Địa chỉ"/"Nơi thường trú" | `Số 12 Đường Lê Lợi, Q1` |
| `phone` | SĐT VN 10-11 số | `0912345678` |
| `email` | chuẩn email | `nam@example.com` |
| `tax_code` | 10-13 số sau "MST" | `0123456789` |

## Độ tin cậy

`validate_field()` kiểm tra tính hợp lệ từng trường:

- **CCCD**: đúng 9 hoặc 12 chữ số
- **Ngày sinh**: năm 1900–2100, tháng 1–12, ngày 1–31, đúng định dạng
- **SĐT**: bắt đầu bằng `0`, 10–11 chữ số
- **Email**: khớp chuẩn `user@domain.tld`
- **Giới tính**: chỉ nhận `Nam`/`Nữ`

`assess_extraction()` tổng hợp thành đánh giá:

| Chất lượng | Điều kiện |
|------------|-----------|
| `high` | Độ tin cậy ≥ 85 và không có trường lỗi |
| `medium` | Độ tin cậy ≥ 60 |
| `low` | Dưới ngưỡng hoặc nhiều trường lỗi |

## Tích hợp pipeline

Trong pipeline (xem `docs/pipeline.md`), trích xuất nằm sau OCR và hậu xử lý:

```
Upload → Validate → Preprocess → OCR → Post-process → **Extract** → Store
```

Dữ liệu sau trích xuất được đánh giá độ tin cậy, các trường nghi ngờ sẽ
được đánh dấu để con người rà soát (phục vụ RE-044 quy trình kiểm duyệt).