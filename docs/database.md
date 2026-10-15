# Thiết kế dữ liệu

```mermaid
erDiagram
  DOCUMENT ||--o{ EXTRACTION : has
  DOCUMENT {
    uuid id PK
    string original_name
    string stored_name UK
    string mime_type
    int size_bytes
    string status
    string document_type
    datetime created_at
    datetime expires_at
  }
  EXTRACTION {
    uuid id PK
    uuid document_id FK
    json data
    json warnings
    string model_version
    bool confirmed
    datetime updated_at
  }
```

`stored_name` không lấy trực tiếp từ input để tránh path traversal. JSON giữ schema
linh hoạt giữa các loại biểu mẫu; các cột trạng thái và loại tài liệu được index
để phục vụ dashboard. `expires_at` mặc định 41 ngày theo RE-044. Việc xóa theo
retention phải xóa cả object và metadata trong một job có audit.
