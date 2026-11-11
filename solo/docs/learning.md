# Tự hiểu và phát triển toàn bộ ứng dụng

Bản cá nhân có mã mới trong `solo/`, giữ lịch sử nhóm ở các thư mục/nhánh cũ.
Các commit mới ghi nhận tác giả theo Git config hiện tại và có trợ giúp AI;
không thay tên tác giả commit khác. Tesseract/VLM là mô hình nền có sẵn, bản
cá nhân là việc thiết kế, triển khai, tích hợp và đánh giá ứng dụng.

## Luồng đọc code

1. `contracts.py`: xem `LABELS`, hai Pydantic models và `validate_values`.
   Thử ngày không tồn tại, tiền có dấu nhóm và một trường bị thiếu bằng pytest.
2. `ocr.py`: bytes → render/EXIF/grayscale → token TSV có confidence. Tesseract
   chạy trong worker; model phải đúng SHA-256, không tự tải khi xử lý tài liệu.
3. `extract.py`: token → dòng → nhãn/giá trị → normalization. Mẫu stacked đọc
   dòng kế khi dòng đó không phải nhãn khác; trường mâu thuẫn không chọn dòng đầu.
4. `vlm.py`: hai request protocol, schema JSON, prompt chống hiểu nội dung ảnh
   thành chỉ dẫn, kiểm tra output. `align_vlm` tìm evidence, `fuse` xử lý bất đồng.
5. `pipeline.py`/`worker.py`: dùng subprocess group để giới hạn toàn lượt xử lý,
   giết và thu hồi process khi hết deadline. CLI/API đều gọi cùng pipeline.
6. `api.py`: catalog, upload, validate, export. Validation chạy lần nữa trên
   snapshot gửi export; JSON giữ original extraction và edited_fields.
7. `web/src/App.tsx`: state file/kind/mode/result/values/validation; mỗi lần đổi
   dữ liệu hủy request cũ. Confidence AI gốc không biến thành confidence của sửa tay.
8. `evaluate.py`: metric null-aware, hash manifest/truth, provenance, taxonomy.
   Đọc một mismatch và đối chiếu ảnh/OCR trước khi kết luận nguyên nhân.

## Các bài thay đổi nhỏ có thể tự làm

- Thêm một alias vào schema ở `LABELS`; viết regression từ token synthetic
  của layout mới, đo trên dev. Nếu đổi luật, tăng rules version/hash được ghi.
- Tạo một schema đơn khác bằng Pydantic, registry và truth synthetic; hiện API
  Kind giới hạn hai loại nên cần mở rộng Kind và catalog/type frontend tương ứng.
- Chọn model, cấu hình adapter, ghi digest/revision rồi so sánh ba chế độ trên
  cùng dataset; không lấy độ tự tin do model tự khai làm xác suất chính xác.
- Tạo bộ challenge synthetic mới có nhãn/giá trị nhiều cột; giữ version/split
  mới, không thay golden-v1. Baseline hiện chưa hỗ trợ đầy đủ loại layout đó.

Mỗi thay đổi: nhánh feature từ `personal/canhtung-solo` → kiểm thử đúng phạm vi
→ stage path cụ thể → xem staged diff → Conventional Commit → push nhánh cá nhân.
Không force push hoặc tự merge vào main chung. File upload/runtime/model/key
không nằm trong Git; chỉ fixture synthetic và baseline được tuyển chọn được commit.
