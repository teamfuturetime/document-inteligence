export const MAX_FILE_BYTES = 10 * 1024 * 1024

export function validateFileSelection(file: File): string | null {
  if (file.size === 0) return 'Tài liệu rỗng. Hãy chọn file khác.'
  if (file.size > MAX_FILE_BYTES) return 'Tài liệu vượt giới hạn 10 MiB.'
  if (!/\.(png|jpe?g|pdf)$/i.test(file.name)) return 'Chỉ hỗ trợ PNG, JPG hoặc PDF.'
  if (file.type && !['image/png', 'image/jpeg', 'application/pdf'].includes(file.type)) {
    return 'Loại tài liệu không được hỗ trợ.'
  }
  return null
}
