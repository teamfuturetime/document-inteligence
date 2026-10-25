# Dataset sản phẩm synthetic 1.0.0

150 parent documents tự thiết kế: 75 hóa đơn header/totals và 75 đơn đề nghị đánh máy. Manifest ở [product.json](../manifests/product.json), tổng 90 development, 30 validation và 30 test. Ba layout mỗi loại; cùng template có thể xuất hiện giữa các splits, không phải phép đo bố cục chưa thấy. Không có hồ sơ thật hoặc danh tính người tham gia thật.

Generator `scripts/generate_product_dataset.py` tạo labels, render từng dòng và kiểm bounding boxes; có blur nhẹ, thiếu trường, vùng bị che và ngày nguồn sai. Gold unreadable không lưu giá trị bí mật trước khi che; absent khác unreadable. Ngày sai nhìn thấy được giữ nguyên trong gold.

PNG và annotation UTF-8/LF có SHA256. Parent IDs được chia trước phép biến đổi; mỗi parent hiện có một ảnh. Giữ số 0, dấu Việt và strict types. Font hệ thống chỉ tham chiếu tên/hash, không phân phối font. Template tự thiết kế, tên/đơn vị/số là hư cấu, có dấu synthetic trên trang.

Generator/labeling cùng nguồn nên cần nhóm review chéo nhãn trước golden nghiệm thu cuối. Lượt này kiểm checksum/schema/bounds và xem mẫu ảnh; không bịa rằng 150 nhãn đã được nhiều người kiểm tra độc lập. Chưa đại diện ảnh chụp thật, chữ viết tay, đa trang hoặc mọi hóa đơn.

Development phục vụ sửa rules; validation chọn policy; test chỉ dùng sau khi chốt. Report nêu split/support/exclusions và model/config/source versions. Tạo lại với font/runtime khác phải tăng dataset version, cập nhật hashes và chạy lại evidence; không sửa gold theo prediction.
