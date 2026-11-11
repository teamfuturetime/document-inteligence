import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

const fields = ['invoice_number', 'invoice_date', 'seller_name', 'total_amount', 'currency']
const labels = ['Số hóa đơn', 'Ngày hóa đơn', 'Bên bán', 'Tổng tiền', 'Tiền tệ']
const values = ['SYN-1', '2026-11-11', 'Cửa hàng Mẫu', 1000, 'VND']
const catalog = { invoice: { title: 'Hóa đơn', fields: fields.map((key, index) => ({ key, label: labels[index], type: key.endsWith('_date') ? 'date' : 'text' })) }, application: { title: 'Đơn đề nghị', fields: [] } }
const extraction = { schema_version: 'solo-1.0', document_type: 'invoice', mode: 'rules', fields: Object.fromEntries(fields.map((key, index) => [key, { value: values[index], confidence: .9, source: 'rules', evidence: ['synthetic'], warnings: [] }])), warnings: [], provenance: {}, ocr_text: 'synthetic' }
const valid = { valid: true, values: Object.fromEntries(fields.map((key, index) => [key, values[index]])), errors: {} }
const response = (payload: unknown) => ({ ok: true, json: async () => payload }) as Response
let fetcher: ReturnType<typeof vi.fn<(path: string, options?: RequestInit) => Promise<Response>>>

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => 'blob:synthetic')
  URL.revokeObjectURL = vi.fn()
  fetcher = vi.fn(async (path: string) => response(path === '/api/schemas' ? catalog : path === '/health'
    ? { ocr: { ready: true }, vlm: { configured: false, provider: 'ollama' } }
    : path === '/api/extract' ? extraction : valid))
  vi.stubGlobal('fetch', fetcher)
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

async function chooseFile() {
  fireEvent.change(screen.getByLabelText('Tải tài liệu mẫu'), { target: { files: [new File(['synthetic'], 'sample.png', { type: 'image/png' })] } })
  await waitFor(() => expect(screen.getByRole('button', { name: /Trích xuất dữ liệu/ })).toBeEnabled())
}

async function extract() {
  await chooseFile()
  fireEvent.click(screen.getByRole('button', { name: /Trích xuất dữ liệu/ }))
  await screen.findByLabelText('Số hóa đơn')
}

test('editing invalidates prior validation and export immediately', async () => {
  render(<App />)
  await extract()
  const exportButton = screen.getByRole('button', { name: /Xuất JSON/ })
  expect(exportButton).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Kiểm tra dữ liệu' }))
  await waitFor(() => expect(exportButton).toBeEnabled())
  fireEvent.change(screen.getByLabelText('Bên bán'), { target: { value: 'Cửa hàng Đã sửa' } })
  expect(exportButton).toBeDisabled()
  expect(screen.getByText(/Bạn đã chỉnh sửa/)).toBeInTheDocument()
})

test('late extraction cannot populate another document', async () => {
  let finish: (value: Response) => void = () => {}
  const standard = fetcher.getMockImplementation()!
  fetcher.mockImplementation((path: string) => path === '/api/extract' ? new Promise(resolve => { finish = resolve }) : standard(path))
  render(<App />)
  await chooseFile()
  fireEvent.click(screen.getByRole('button', { name: /Trích xuất dữ liệu/ }))
  fireEvent.change(screen.getByLabelText('Tải tài liệu mẫu'), { target: { files: [new File(['new'], 'new.png', { type: 'image/png' })] } })
  finish(response(extraction))
  await waitFor(() => expect(screen.getByText('new.png')).toBeInTheDocument())
  expect(screen.queryByLabelText('Số hóa đơn')).not.toBeInTheDocument()
})

test('late validation after an edit cannot re-enable export', async () => {
  let finish: (value: Response) => void = () => {}
  const standard = fetcher.getMockImplementation()!
  fetcher.mockImplementation((path: string) => path === '/api/validate' ? new Promise(resolve => { finish = resolve }) : standard(path))
  render(<App />)
  await extract()
  fireEvent.click(screen.getByRole('button', { name: 'Kiểm tra dữ liệu' }))
  fireEvent.change(screen.getByLabelText('Bên bán'), { target: { value: 'Mẫu khác' } })
  finish(response(valid))
  await waitFor(() => expect(screen.getByRole('button', { name: /Xuất JSON/ })).toBeDisabled())
})

test('unconfigured VLM and oversized files do not silently use rules', async () => {
  render(<App />)
  await chooseFile()
  fireEvent.change(screen.getByLabelText('Phương pháp'), { target: { value: 'vlm' } })
  expect(screen.getByText(/VLM chưa cấu hình/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Trích xuất dữ liệu/ })).toBeDisabled()
  expect(fetcher.mock.calls.some(call => call[0] === '/api/extract')).toBe(false)
  const large = new File(['x'], 'large.png', { type: 'image/png' })
  Object.defineProperty(large, 'size', { value: 11 * 1024 * 1024 })
  fireEvent.change(screen.getByLabelText('Tải tài liệu mẫu'), { target: { files: [large] } })
  expect(screen.getByRole('alert')).toHaveTextContent('File vượt 10 MiB')
})

test('switching OCR provider clears extraction and prior validation', async () => {
  render(<App />)
  await extract()
  fireEvent.click(screen.getByRole('button', { name: 'Kiểm tra dữ liệu' }))
  await waitFor(() => expect(screen.getByRole('button', { name: /Xuất JSON/ })).toBeEnabled())
  fireEvent.change(screen.getByLabelText('Nguồn OCR'), { target: { value: 'ocrspace' } })
  expect(screen.queryByLabelText('Số hóa đơn')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Xuất JSON/ })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Trích xuất dữ liệu/ })).toBeDisabled()
  expect(screen.getByText(/Tài liệu sẽ được gửi đến OCR.space/)).toBeInTheDocument()
})

test('configured cloud selection sends provider only and displays unavailable confidence', async () => {
  const standard = fetcher.getMockImplementation()!
  fetcher.mockImplementation(async (path, options) => {
    if (path === '/health') return response({ ocr: { ready: false },
      ocr_providers: { tesseract: { ready: false }, ocrspace: { ready: true, configured: true } },
      vlm: { configured: false } })
    if (path === '/api/extract') {
      expect((options?.body as FormData).get('ocr_provider')).toBe('ocrspace')
      expect((options?.body as FormData).has('apikey')).toBe(false)
      return response({ ...extraction, fields: Object.fromEntries(Object.entries(extraction.fields).map(([key, field]) => [key, { ...field, confidence: null, warnings: key === 'seller_name' ? ['Cần đối chiếu dấu tiếng Việt với bản gốc.'] : [] }])), provenance: { ocr: { provider: 'ocrspace' } } })
    }
    return standard(path, options)
  })
  render(<App />)
  await screen.findByText(/Nguồn OCR chưa sẵn sàng/)
  fireEvent.change(screen.getByLabelText('Nguồn OCR'), { target: { value: 'ocrspace' } })
  await chooseFile()
  fireEvent.click(screen.getByRole('button', { name: /Trích xuất dữ liệu/ }))
  await screen.findByLabelText('Số hóa đơn')
  expect(screen.getAllByText('Chưa có confidence')).toHaveLength(5)
  expect(screen.getByText(/OCR.space không cung cấp confidence/)).toBeInTheDocument()
  expect(screen.getByText('Cần đối chiếu dấu tiếng Việt với bản gốc.')).toBeVisible()
})

test('OCR selection waits for backend settings so a late health response cannot overwrite a choice', async () => {
  let release: (value: Response) => void = () => {}
  const standard = fetcher.getMockImplementation()!
  fetcher.mockImplementation((path, options) => path === '/health'
    ? new Promise(resolve => { release = resolve }) : standard(path, options))
  render(<App />)
  expect(screen.getByLabelText('Nguồn OCR')).toBeDisabled()
  release(response({ ocr: { ready: true, provider: 'ocrspace' },
    ocr_providers: { tesseract: { ready: true }, ocrspace: { ready: true } }, vlm: { configured: false } }))
  await waitFor(() => expect(screen.getByLabelText('Nguồn OCR')).toBeEnabled())
  expect(screen.getByLabelText('Nguồn OCR')).toHaveValue('ocrspace')
  fireEvent.change(screen.getByLabelText('Nguồn OCR'), { target: { value: 'tesseract' } })
  expect(screen.getByLabelText('Nguồn OCR')).toHaveValue('tesseract')
})

test('a late sample download cannot replace a file chosen by the user', async () => {
  let release: (value: Response) => void = () => {}
  const standard = fetcher.getMockImplementation()!
  fetcher.mockImplementation((path, options) => path.endsWith('samples/invoice-001.png')
    ? new Promise(resolve => { release = resolve }) : standard(path, options))
  render(<App />)
  fireEvent.click(screen.getByRole('button', { name: /Dùng hóa đơn mẫu/ }))
  await chooseFile()
  release({ ok: true, blob: async () => new Blob(['sample'], { type: 'image/png' }) } as Response)
  await waitFor(() => expect(screen.getByText('sample.png')).toBeInTheDocument())
  expect(screen.queryByText('invoice-001.png')).not.toBeInTheDocument()
  expect(fetcher.mock.calls.some(call => call[0] === '/api/extract')).toBe(false)
})

test('dropping a different file clears reviewed data and multiple files are rejected', async () => {
  render(<App />)
  await extract()
  fireEvent.click(screen.getByRole('button', { name: 'Kiểm tra dữ liệu' }))
  await waitFor(() => expect(screen.getByRole('button', { name: /Xuất JSON/ })).toBeEnabled())
  const preview = screen.getByAltText('Bản xem trước sample.png').closest('.preview')!
  const next = new File(['new'], 'dropped.pdf', { type: 'application/pdf' })
  fireEvent.drop(preview, { dataTransfer: { files: [next] } })
  expect(screen.queryByLabelText('Số hóa đơn')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Xuất JSON/ })).not.toBeInTheDocument()
  expect(screen.getByText('dropped.pdf')).toBeInTheDocument()
  fireEvent.drop(preview, { dataTransfer: { files: [next, next] } })
  expect(screen.getByRole('alert')).toHaveTextContent('Mỗi lần chỉ chọn một tài liệu')
  expect(screen.getByRole('button', { name: /Trích xuất dữ liệu/ })).toBeDisabled()
})
