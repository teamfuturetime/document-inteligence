# ADR-0005 — Baseline OCR và rules trước thí nghiệm VLM

**Status:** Strategy proposed; PROVISIONAL, chưa triển khai engine. **Links:** MVP-01/02, BL-002/003/004/011.

**Context:** cần phân biệt chữ OCR với mapping, chi phí và nguồn sai; chưa có baseline. **Options:** Tesseract/PaddleOCR sau spike; rules nhãn/vị trí; VLM/LLM mở rộng nếu chứng minh có lợi. **Decision:** interface trước; chọn OCR theo mẫu tiếng Việt và môi trường; rules giữ alias/spatial/multiline/candidates/abstain, không hard-code theo ID. **Consequences:** baseline có thể giải thích/tái lập; benchmark trước kết luận; chưa tải model hoặc gọi dịch vụ AI. **Revisit conditions:** errors baseline cho thấy VLM có hypothesis cải thiện đo được, data policy/budget cho phép; giữ baseline để so sánh.
