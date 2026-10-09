# Shared contracts

Owner: Backend; Technical Lead điều phối review Frontend/Extraction.

Contract v1.0.0 tại `v1/`; fixtures và manifest tại `fixtures/`.
Pydantic models ở `src/document_contracts/models.py` là nguồn xuất schema,
đóng gói thành `document-contracts` độc lập với backend/FastAPI.
Không sửa schema sinh ra bằng tay. Xem [contract và lệnh kiểm tra](../docs/contracts.md).
Đây là interface baseline local, chưa có API/OCR chạy hoặc review nhóm.
