# Pipeline xử lý tài liệu

## 1. Sơ đồ luồng dữ liệu

```
┌──────────┐   Upload    ┌──────────┐  Validate  ┌──────────┐
│  Người   │ ──────────▶ │ Backend  │ ─────────▶ │ Storage  │
│  dùng    │             │ FastAPI  │            │  File +  │
└──────────┘             └────┬─────┘            │ Postgres │
                             │                  └──────────┘
                             ▼
                    ┌─────────────────┐
                    │   AI Service    │
                    └──┬──────┬───────┘
                       │      │
              ┌────────▼──┐ ┌─▼──────────┐
              │ Preprocess│ │    OCR     │
              │ (OpenCV)  │ │ (PaddleOCR)│
              └───────────┘ └─┬──────────┘
                              │ text + boxes
                    ┌─────────▼──────────┐
                    │ Classification     │
                    └─────────┬──────────┘
                    ┌─────────▼──────────┐
                    │ Extraction (JSON)  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Normalization      │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ User review/confirm│
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ PostgreSQL + File  │
                    └───────────────────┘
```

## 2. Các bước chi tiết

### Bước 1: Upload (Backend)
- Nhận file PDF/JPG/JPEG/PNG qua `POST /api/v1/documents/upload`.
- Kiểm tra loại file thực tế (magic bytes), kích thước ≤ 10MB.
- Lưu file vào storage, tạo bản ghi `Document` (status = `uploaded`).

### Bước 2: Tiền xử lý (AI Service)
- PDF → ảnh qua PyMuPDF (DPI 200).
- Ảnh: chuyển grayscale, tăng tương phản, khử nhiễu.
- Hiệu chỉnh nghiêng (deskew) bằng OpenCV Hough transform.

### Bước 3: OCR (AI Service)
- PaddleOCR với ngôn ngữ `vietnamese`.
- Kết quả: danh sách text block kèm bounding box `[x1, y1, x2, y2]`.
- Chuẩn hóa Unicode (chuẩn NFC), sửa lỗi dấu tiếng Việt phổ biến.
- Fallback: nếu không có PaddleOCR, dùng engine đơn giản để MVP chạy được.

### Bước 4: Phân loại biểu mẫu (AI Service)
- Dựa trên từ khóa và cấu trúc bố cục.
- Các loại: `invoice`, `contract`, `application_form`, `report`, `unknown`.

### Bước 5: Trích xuất (AI Service)
- Áp dụng JSON Schema theo loại biểu mẫu.
- Trích xuất trường dữ liệu (tên, ngày, số tiền, mã số...).
- Kết quả JSON có cấu trúc + độ tin cậy từng trường.

### Bước 6: Chuẩn hóa (Backend)
- Chuẩn hóa định dạng ngày, số tiền, mã.
- Lưu `Extraction` record (status = `pending_review`).

### Bước 7: Xác nhận (Người dùng)
- Xem kết quả, chỉnh sửa trường sai.
- Xác nhận → status = `confirmed`, lưu vĩnh viễn.

### Bước 8: Lưu trữ & tìm kiếm
- Metadata trong PostgreSQL, file trong storage.
- Tìm kiếm theo tên, loại, trạng thái, ngày.

## 3. Trạng thái tài liệu

| Trạng thái | Ý nghĩa |
|------------|---------|
| `uploaded` | Đã upload, chưa xử lý |
| `processing` | Đang xử lý (preprocess/OCR/AI) |
| `processed` | Đã trích xuất xong, chờ xác nhận |
| `confirmed` | Người dùng đã xác nhận |
| `failed` | Xử lý lỗi |

## 4. Xử lý lỗi

- File không hợp lệ → `400 Bad Request` với thông báo rõ ràng.
- AI Service lỗi → retry 2 lần, sau đó đánh dấu `failed` và log lỗi.
- Database lỗi → rollback transaction, trả `500` với mã lỗi.
- Mọi lỗi đều được ghi log có cấu trúc (JSON), không ghi nội dung tài liệu.

## 5. Ràng buộc RE-044

- **421 người dùng đồng thời**: xử lý bất đồng bộ, giới hạn kích thước upload, pool kết nối DB.
- **Lưu giữ 41 ngày**: script `scripts/retention.py` xóa tài liệu quá hạn.
- **Change request trong 18 giờ**: quy trình ghi nhận và phản hồi được mô tả trong docs.
