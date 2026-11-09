import{describe,expect,it}from'vitest';import{validateUpload}from'./files';
describe('validateUpload',()=>{it('chấp nhận PDF hợp lệ',()=>expect(validateUpload(new File(['%PDF'],'mau.pdf',{type:'application/pdf'}))).toBeNull());it('từ chối định dạng lạ',()=>expect(validateUpload(new File(['x'],'x.txt',{type:'text/plain'}))).toContain('Chỉ hỗ trợ'));it('từ chối file quá lớn',()=>expect(validateUpload(new File([new Uint8Array(11*1024*1024)],'x.png',{type:'image/png'}))).toContain('10 MB'))})

describe('extended image formats', () => {
  it.each([
    ['webp', 'image/webp'], ['bmp', 'image/bmp'], ['BMP', 'image/x-ms-bmp'],
    ['tif', 'image/tiff'], ['tiff', 'image/tiff'], ['tiff', ''],
    ['tif', 'application/octet-stream'], ['png', 'image/png'],
    ['jpg', 'image/jpeg'], ['jpeg', 'image/jpeg'],
  ])('accepts %s with MIME %s', (extension, type) => {
    expect(validateUpload(new File(['data'], 'scan.' + extension, { type }))).toBeNull()
  })
  it.each([
    ['scan.gif', 'image/gif'], ['scan.heic', 'image/heic'], ['scan.heif', 'image/heif'],
    ['scan.exe', 'image/png'], ['scan.webp', 'image/png'], ['scan.tif', 'text/plain'],
  ])('rejects %s with MIME %s', (name, type) => {
    expect(validateUpload(new File(['data'], name, { type }))).toContain('Chỉ hỗ trợ')
  })
  it('rejects empty files', () => {
    expect(validateUpload(new File([], 'empty.tiff', { type: 'image/tiff' }))).toContain('rỗng')
  })
  it('keeps the 10 MB boundary', () => {
    expect(validateUpload(new File([new Uint8Array(10 * 1024 * 1024)], 'scan.tif', { type: 'image/tiff' }))).toBeNull()
    expect(validateUpload(new File([new Uint8Array(10 * 1024 * 1024 + 1)], 'scan.tif', { type: 'image/tiff' }))).toContain('10 MB')
  })
})
