const labels: Record<string, string> = {
  invoice_number: 'Số hóa đơn', issue_date: 'Ngày lập', seller: 'Đơn vị bán',
  address: 'Địa chỉ', total_amount: 'Tổng tiền thanh toán', vat: 'Thuế VAT',
  vat_rate: 'Thuế suất VAT', payment_method: 'Phương thức thanh toán',
  tax_code: 'Mã số thuế', cccd: 'Số định danh / CCCD', full_name: 'Họ và tên',
  birth_date: 'Ngày sinh', gender: 'Giới tính', nationality: 'Quốc tịch',
  hometown: 'Quê quán', form_name: 'Tên biểu mẫu', content: 'Nội dung chính',
  phone: 'Điện thoại', email: 'Email',
}

export const extractedFieldLabel = (key: string) => labels[key] || key.replaceAll('_', ' ')
export const emptyExtractionMessage = 'Chưa tìm được trường dữ liệu có căn cứ trong OCR. Chọn “Chỉnh sửa dữ liệu”, sau đó “Thêm trường” để nhập thủ công.'

export function extractionNotice(status?: string, source?: string) {
  if (status === 'confirmed') return 'Dữ liệu đã được người dùng xác nhận.'
  if (status === 'reviewed') return 'Dữ liệu đã được lưu rà soát; chưa được xác nhận.'
  if (source === 'manual') return 'Dữ liệu nhập thủ công; chưa được xác nhận.'
  return 'Các trường do máy trích xuất; hãy đối chiếu và rà soát trước khi xác nhận.'
}
