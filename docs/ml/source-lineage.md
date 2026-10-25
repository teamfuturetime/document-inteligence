# Nguồn kế thừa và trách nhiệm thay đổi

Lượt triển khai trên nhatquang ngày 24/10/2026 thực hiện theo yêu cầu mới: triển khai cả sản phẩm trên nhánh này; không phải xác nhận nhóm đã merge nền hoặc đã phân công lại trên GitHub.

| Nguồn | Phần được sử dụng hoặc đối chiếu | Phần thay đổi trong nhatquang |
| --- | --- | --- |
| nhatquang tại f37bfbd | FastAPI/React foundation, contracts từ Pydantic, fixtures, normalization, validation, evaluator và quy tắc review/provenance | Giữ fixture riêng; thêm workflow sản phẩm, SQLite, actual OCR, review/confirm/export và UI |
| personal/canhtung-main tại 61a31ab | Đọc code pipeline/ocr.py, preprocessing.py, runner.py, extraction.py và model lock để đối chiếu | Giữ pin tessdata_fast revision/checksums từ model lock; triển khai adapter vào contracts hiện tại, worker ảnh và typed inference DTO riêng |
| Model lock của Tùng | tessdata_fast revision 87416418657359cb625c412a48b6e1d6d41c29bd, vie/eng SHA256 | Không ghi nhận việc chọn revision/hash này như đóng góp mới của Quang; download helper xác minh bytes thật từ nguồn chính thức |
| Tesseract/Pillow chính thức | CLI TSV, LSTM OEM1, PSM và image decoding | Sửa khả năng nhận version Windows có tiền tố v; xử lý đường dẫn Unicode bằng model temp ASCII có checksum và cleanup |
| congtri/minhthao/tuannguyen | Đọc Git snapshot để nhận biết các phần đang được thành viên phát triển | Không copy toàn bộ backend/frontend/evaluator khác, không merge nhánh hoặc thay lịch sử của ai |

Không import nguyên ứng dụng Tùng hoặc thêm package document_contracts thứ hai cạnh domain models hiện tại. `pipeline.models` là DTO nội bộ inference; public HTTP contracts vẫn ở backend domain. `docintel.adapters.pipeline` là điểm chuyển đổi duy nhất. Khi nhóm chốt một nền khác, dùng adapter và bảng ánh xạ trong [handoff](../product/integration-handoff.md), không giữ hai app production chạy song song.

Tham chiếu: [Tesseract CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [Tesseract image quality](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), [Pillow Image](https://pillow.readthedocs.io/en/stable/reference/Image.html). Nguồn kỹ thuật không thay rubric hoặc tạo ra benchmark.
