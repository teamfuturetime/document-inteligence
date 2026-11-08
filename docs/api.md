# REST API

Base URL: `/api/v1`

| Method | Path | Mô tả |
|---|---|---|
| POST | `/documents` | Upload PDF/PNG/JPEG multipart field `file` |
| GET | `/documents` | Tìm kiếm, lọc, phân trang |
| GET | `/documents/{id}` | Metadata tài liệu |
| GET | `/documents/{id}/content` | Xem hoặc tải file gốc |
| POST | `/documents/{id}/process` | Chạy pipeline |
| GET | `/documents/{id}/extraction` | JSON extraction mới nhất |
| PATCH | `/documents/{id}/extraction` | Sửa giá trị các trường đã trích xuất |
| POST | `/documents/{id}/confirm` | Xác nhận và khóa kết quả |

OpenAPI tương tác có tại `/docs`. Lỗi dùng cấu trúc FastAPI `{ "detail": ... }`.

## Tìm kiếm và phân trang

`GET /documents` nhận `q` (tên gần đúng hoặc ID chính xác), `status`,
`document_type`, `offset` (từ 0) và `limit` (1–100, mặc định 20).
Các bộ lọc kết hợp bằng AND. Response là `{ "items": [...], "total": 12 }`;
`total` là tổng số tài liệu phù hợp trước khi phân trang. Thứ tự giảm dần theo
`created_at`, sau đó `id` để phân trang ổn định khi timestamp trùng nhau.

```text
GET /documents?document_type=invoice&status=review&offset=0&limit=10
```

## Xử lý và trạng thái

`POST /documents/{id}/process` nhận tài liệu ở trạng thái `uploaded`, `review`
hoặc `failed`. API giữ chỗ bằng conditional UPDATE và commit trước OCR để các
worker không cùng nhận một tài liệu. Trạng thái `processing` và `confirmed`
trả `409`; ID không tồn tại trả `404`.

Pipeline vẫn chạy đồng bộ trong request, trả `202` khi xử lý xong và tài liệu
ở trạng thái `review`. Nếu pipeline/lưu extraction thất bại, API rollback dữ
liệu chưa commit, cố gắng ghi trạng thái `failed` rồi trả `503`. Có thể gọi lại
endpoint để thử lại; lỗi database kéo dài có thể ngăn việc ghi trạng thái lỗi.

## Chỉnh sửa và xác nhận

`PATCH /documents/{id}/extraction` yêu cầu `data.fields` là object tối đa 100
trường; mỗi trường gửi lên phải có `confidence` trong `[0, 1]` như cấu trúc kết
quả đọc được. Có thể gửi một phần các trường:

```json
{
  "data": {
    "fields": {
      "customer": { "value": "Công ty An Phú", "confidence": 0.8 }
    }
  }
}
```

API chỉ áp dụng `value` cho trường đã tồn tại; trường không được gửi vẫn giữ
nguyên. Thay đổi giá trị đặt `reviewed: true`. Metadata OCR (`raw_text`, `pages`,
`document_type`, `model_version`, `confidence`, `source_text`) và cảnh báo không
thể bị ghi đè từ client. Cảnh báo thiếu trường được tính lại từ các giá trị đã
lưu và đồng bộ ở cả `data.warnings` lẫn `warnings` của response. Trường không
hợp lệ hoặc trường mới ngoài kết quả trích xuất trả `422`.

Sửa và xác nhận được tuần tự hóa với thao tác xử lý trên cùng tài liệu. Chỉ
trạng thái `review` được sửa/xác nhận; trạng thái khác trả `409`.
`POST /documents/{id}/confirm` đặt extraction `confirmed: true` và tài liệu
`status: confirmed`. Gọi xác nhận lại trả kết quả hiện tại (`200`). Sau khi xác
nhận, sửa hoặc nhận diện lại trả `409`; muốn xử lý bản mới cần upload lại.

Nếu đặt `API_KEY`, mọi endpoint tài liệu yêu cầu header `X-API-Key`.
