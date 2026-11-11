# Golden synthetic v1

36 tài liệu mới, độc lập với dataset của ứng dụng tích hợp: 18 hóa đơn và 18 đơn
đề nghị sinh viên. Mỗi loại có 9 dev / 9 test; mỗi split gồm ba layout (có dấu
hai chấm, không dấu hai chấm, giá trị dòng kế) × ba điều kiện (rõ, mờ nhẹ,
thiếu trường). PNG/JPEG/PDF phân bố đều, không gắn một định dạng với một layout.

Tất cả tên/ID/nội dung là tổng hợp, có nhãn trong ảnh. Ground truth được sinh
từ nội dung trước OCR, tác giả kiểm tra; review độc lập chưa thực hiện. Manifest
lưu SHA-256 của cả tài liệu và ground truth. Không thay đổi split/ground truth
hoặc chỉnh test để đạt chỉ số. Chạy baseline sau khi commit dataset đã freeze.

Tái tạo ở **thư mục mới** từ `solo/` với Pillow theo lockfile và đúng font có
SHA-256 ghi trong manifest (Arial macOS, không phân phối font):

```bash
uv run python data/generate.py --font '/System/Library/Fonts/Supplemental/Arial.ttf' --output data/generated-v1
```

Generator từ chối ghi đè thư mục có dữ liệu. Giữ file dataset đã commit khi chạy
Linux/CI; không cần font để OCR/evaluate các tài liệu này. Dataset nhỏ, chưa đại
diện mọi hóa đơn/đơn từ và chưa chứng minh khả năng tổng quát trên layout mới.
