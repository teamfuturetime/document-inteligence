export const allowedTypes = ['application/pdf','image/png','image/jpeg']
export function validateUpload(file:File,maxBytes=10*1024*1024):string|null{if(!allowedTypes.includes(file.type))return 'Chỉ hỗ trợ PDF, JPG, JPEG hoặc PNG.';if(file.size>maxBytes)return 'File không được vượt quá 10 MB.';return null}
