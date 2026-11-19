const guidance: Record<string, string> = {
  PROVIDER_UNAVAILABLE:
    'OCR chưa sẵn sàng. Nhờ người quản lý kiểm tra Tesseract và model vie/eng theo README. Sau khi khắc phục, chọn Chạy OCR lại.',
  MODEL_HASH_MISMATCH:
    'Model OCR không đúng phiên bản. Nhờ người quản lý kiểm tra checksum và cài lại model đã pin theo README trước khi chạy lại.',
  INPUT_CHANGED:
    'Ảnh nguồn đã thay đổi so với bản lưu. Chạy lại trên bản này sẽ không khắc phục được. Giữ bản nháp, nhờ người quản lý kiểm tra hoặc tự chọn tải lên ảnh gốc thành tài liệu mới.',
  PROCESSING_INTERRUPTED:
    'OCR bị gián đoạn khi ứng dụng dừng. Sau khi ứng dụng ổn định, chọn Chạy OCR lại để tạo lần xử lý mới.',
  PROCESSING_TIMEOUT:
    'OCR vượt thời gian xử lý. Thử ảnh một trang rõ nét, gọn hơn trong giới hạn tải lên; hoặc chọn Chạy OCR lại. Nếu lặp lại, nhờ người quản lý kiểm tra tài nguyên.',
  INVALID_OCR_OUTPUT:
    'Kết quả OCR không hợp lệ. Chọn Chạy OCR lại; nếu lỗi lặp lại, nhờ người quản lý kiểm tra engine và model.',
  PROVIDER_FAILED:
    'Engine OCR không xử lý được ảnh. Kiểm tra ảnh có đọc được và chọn Chạy OCR lại; nếu vẫn lỗi, nhờ người quản lý kiểm tra engine.',
  INVALID_DOCUMENT:
    'Không đọc được ảnh. Giữ bản nháp và tự chọn tải lên ảnh PNG/JPG một trang hợp lệ thành tài liệu mới.',
  FILE_TOO_LARGE:
    'Ảnh vượt giới hạn dung lượng. Tự chọn ảnh nhỏ hơn trong giới hạn tải lên; tài liệu và bản nháp hiện tại được giữ.',
  IMAGE_TOO_LARGE:
    'Ảnh vượt giới hạn số điểm ảnh. Tự chọn ảnh có độ phân giải thấp hơn; giữ ảnh gốc để đối chiếu.',
  UNSUPPORTED_SCHEMA:
    'Loại tài liệu chưa được hỗ trợ. Tự chọn loại tài liệu được hỗ trợ khi tải ảnh mới.',
  PROCESSING_FAILED:
    'OCR chưa hoàn tất do lỗi xử lý. Chọn Chạy OCR lại khi đã sẵn sàng; nếu lặp lại, nhờ người quản lý kiểm tra.',
};

export function OcrErrorGuidance({
  code,
  requestId,
}: {
  code?: string | null;
  requestId?: string;
}) {
  return (
    <div className="notice" role="alert" aria-atomic="true">
      <p>
        {code && Object.hasOwn(guidance, code)
          ? guidance[code]
          : 'Chưa xác định được lỗi OCR. Giữ bản nháp và nhờ người quản lý kiểm tra trước khi chọn Chạy OCR lại.'}
      </p>
      <p>
        Bản lưu và chỉnh sửa hiện tại được giữ. Hệ thống không tự gửi lại thao tác ghi. Hãy lưu hoặc
        đối chiếu chỉnh sửa trước khi chạy OCR lại.
      </p>
      {requestId && /^[a-zA-Z0-9_-]{1,128}$/.test(requestId) && (
        <p>
          Mã yêu cầu hỗ trợ: <code>{requestId}</code>
        </p>
      )}
    </div>
  );
}
