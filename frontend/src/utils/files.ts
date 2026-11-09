const mimeByExtension: Record<string, string[]> = {
  pdf: ['application/pdf'], png: ['image/png'], jpg: ['image/jpeg'], jpeg: ['image/jpeg'],
  webp: ['image/webp'], bmp: ['image/bmp', 'image/x-bmp', 'image/x-ms-bmp'],
  tif: ['image/tiff', 'image/x-tiff'], tiff: ['image/tiff', 'image/x-tiff'],
}
export const allowedTypes = [...new Set(Object.values(mimeByExtension).flat())]
export const uploadAccept = Object.keys(mimeByExtension).map(extension => '.' + extension).join(',')

export function validateUpload(file: File, maxBytes = 10 * 1024 * 1024): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase() || ''
  const types = mimeByExtension[extension]
  if (!types || (file.type && file.type !== 'application/octet-stream' && !types.includes(file.type))) {
    return 'Chỉ hỗ trợ PDF, PNG, JPG, JPEG, WebP, BMP và TIFF.'
  }
  if (file.size === 0) return 'File rỗng, không thể xử lý.'
  if (file.size > maxBytes) return 'File không được vượt quá 10 MB.'
  return null
}
