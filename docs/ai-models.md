# Mô hình AI và chế độ chạy

MVP dùng PaddleOCR tiếng Việt qua adapter lazy-load. Phân loại và extraction dùng
rule có version (`rules-v1`), dễ audit và không gửi dữ liệu cá nhân ra dịch vụ
ngoài. Kiến trúc `DocumentIntelligence` cho phép thay classifier/extractor bằng
mô hình layout-aware hoặc LLM nội bộ mà không đổi API.

Không có model weight trong repository. Cài `backend/requirements-ocr.txt` và
PaddlePaddle đúng nền tảng, đặt `OCR_ENGINE=paddle`, rồi dùng dataset đã gắn nhãn
để đo CER/WER và field F1. Không coi output từ `EmptyOcrEngine` là kết quả OCR.
