# Phân loại tài liệu

`DocumentClassifier` chuẩn hóa Unicode/case/khoảng trắng và bỏ dấu để chịu lỗi OCR
tiếng Việt, sau đó chấm điểm keyword (1.0) và regex (1.5). Các loại hiện có:
`cccd`, `cmnd`, `hop_dong_lao_dong`, `don_xin_viec`, `ho_khau`, và `unknown`.

```python
result = build_vietnamese_classifier().classify(ocr_text)
```

Hợp đồng `ClassificationResult`:

| Field | Ý nghĩa |
|---|---|
| `document_type` | Nhãn hoặc `unknown` |
| `raw_score` | Tổng trọng số luật của nhãn đứng đầu |
| `confidence` | Ước lượng heuristic 0–100, tối đa 95 |
| `confidence_type` | `heuristic`, không phải xác suất đã hiệu chuẩn |
| `matched_rules` | Keyword/regex thực sự đã khớp |
| `needs_review` | Bằng chứng yếu, gần điểm, hòa điểm hoặc dưới ngưỡng |
| `scores` | Raw score của mọi nhãn để audit |

Confidence kết hợp coverage luật, khoảng cách với nhãn thứ hai và lượng bằng chứng.
Không có dataset gán nhãn nên không được dùng số này như accuracy. Không có bằng
chứng hoặc hòa điểm trả `unknown`; khoảng cách dưới 30% yêu cầu rà soát.

`DocumentTypeDetector` là API tương thích cho bộ pattern chi tiết. Pipeline chính
dùng trực tiếp hợp đồng classifier để tránh hai lần diễn giải confidence.
