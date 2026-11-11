# Hai adapter VLM — cấu hình sau

Quyết định của chủ dự án: chuẩn bị cả adapter local và API, chưa chọn/cài model
hoặc gọi dịch vụ có phí. Kiểm thử hiện tại xác nhận request/response, ảnh base64,
JSON Schema, revision và xử lý lỗi bằng transport giả lập. **Chưa có bằng chứng
model thật trích xuất đúng, tốc độ thực tế hoặc so sánh chất lượng VLM/hybrid.**

Mặc định chưa có `SOLO_VLM_MODEL`, vì vậy UI khóa extraction VLM và backend trả
503 nếu gọi trực tiếp. Mode rules vẫn chạy hoàn toàn local. Không fallback ngầm.
Sau khi đổi env cần khởi động lại backend và tải lại trang web.

## Local qua Ollama

Cài Ollama và tải model vision do bạn chọn; tham khảo ứng viên nhỏ
[Qwen3-VL 2B](https://ollama.com/library/qwen3-vl:2b). Dung lượng model khoảng
1,9 GB không đồng nghĩa tổng RAM cần dùng; phải đo trên M1 8 GB trước khi chốt.
Ứng dụng không tự cài runtime hoặc pull model khi upload.

```bash
export SOLO_VLM_PROVIDER=ollama
export SOLO_VLM_URL=http://127.0.0.1:11434
export SOLO_VLM_MODEL=qwen3-vl:2b
# Sau lần đo đầu, khóa digest đầy đủ từ /api/tags hoặc provenance.vlm.model_revision:
# export SOLO_VLM_REVISION=<digest-đầy-đủ>
uv run --locked uvicorn ai02_solo.api:app --host 127.0.0.1 --port 8100
```

Adapter xác nhận model trong `/api/tags`, ghi digest thực tế và runtime version;
nếu đã khóa revision mà model đổi thì từ chối chạy. REST `/api/chat` gửi ảnh PNG
đã preprocessing, OCR context, prompt version/hash và JSON Schema trong `format`.
Temperature=0, seed=11, context=4096, output tối đa 1024 token, unload sau request.
Đây là cấu hình khởi điểm để đo, chưa phải cấu hình đã tối ưu.

## API multimodal từ xa

Server cần hỗ trợ giao thức chat completions có `image_url` data URL và
`response_format.type=json_schema` (ví dụ một deployment vLLM vision phù hợp).
Không giả định mọi API tương thích đều hỗ trợ structured output cho ảnh.

```bash
export SOLO_VLM_PROVIDER=remote
export SOLO_VLM_URL=https://your-vlm-server.example/v1
export SOLO_VLM_MODEL=your-vision-model
export SOLO_VLM_REVISION=your-immutable-deployment-revision
# Đặt SOLO_VLM_API_KEY trong môi trường riêng nếu server yêu cầu; không commit key.
uv run --locked uvicorn ai02_solo.api:app --host 127.0.0.1 --port 8100
```

Revision remote là thông tin do người vận hành khai báo, không phải hash trọng
số do ứng dụng tự kiểm chứng. HTTP chỉ cho localhost; remote bắt buộc HTTPS,
không theo redirect mang key. Giới hạn response 1 MiB, deadline toàn pipeline
mặc định 120s (SOLO_DEADLINE, 10–300s). URL/key không trả về trình duyệt/report.

VLM luôn gửi **ảnh**, không chỉ gửi OCR text rồi gọi là vision. JSON sai kiểu,
thừa/thiếu key, markdown hoặc output bị cắt bị từ chối. Giá trị không đúng quy
tắc schema thành null kèm cảnh báo. Không dùng confidence tự khai của VLM;
chỉ có score khi tìm được evidence OCR, ghi rõ nguồn. VLM-only vẫn cần OCR để
có context/evidence. Hybrid giữ null khi hai nguồn bất đồng; chỉ nhận bổ sung
từ VLM khi có evidence OCR. Vì thế lỗi OCR mất dấu có thể vẫn chưa được hybrid
sửa; cần đo riêng ba chế độ và rà soát thủ công.

Sau cấu hình, chạy trước trên dev:

```bash
uv run --locked python -m ai02_solo.evaluate --split dev --mode vlm --output evaluation/reports/dev-vlm.json
uv run --locked python -m ai02_solo.evaluate --split dev --mode hybrid --output evaluation/reports/dev-hybrid.json
```

Nguồn giao thức: [Ollama vision](https://docs.ollama.com/capabilities/vision),
[Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[vLLM multimodal inputs](https://docs.vllm.ai/en/latest/features/multimodal_inputs/),
[vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/).
