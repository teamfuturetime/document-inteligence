import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import extraction from '../../../../schemas/fixtures/extraction-success.json'
import validFixture from '../../../../schemas/fixtures/validation-success.json'
import { InvoiceReview } from './InvoiceReview'
import { DocumentPreview } from './DocumentPreview'
import { reviewedExport, validateReviewedValues } from '../../api/client'
import type { ExtractionResponse } from '../../api/generated/extraction-response'
import type { ValidationResponse } from '../../api/generated/validation-response'

const result = extraction as ExtractionResponse
const valid = validFixture as ValidationResponse

it('requires validation, preserves AI provenance and invalidates after edit/reset', async () => {
  const fetch = vi.fn().mockResolvedValue(Response.json(valid))
  vi.stubGlobal('fetch', fetch)
  const user = userEvent.setup()
  render(<InvoiceReview result={result} />)
  const download = screen.getByRole('button', { name: 'Xuất JSON đã xác nhận' })
  expect(download).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Kiểm tra dữ liệu' }))
  expect(await screen.findByText('Dữ liệu hợp lệ. Có thể xuất JSON.')).toBeVisible()
  expect(download).toBeEnabled()
  const [, options] = fetch.mock.calls[0]
  expect(options.headers['Content-Type']).toBe('application/json')
  expect(JSON.parse(options.body).values.total_amount).toBe('125000')
  await user.type(screen.getByLabelText('Bên bán'), ' mới')
  expect(download).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Khôi phục kết quả gốc' }))
  expect(screen.getByLabelText('Bên bán')).toHaveValue(result.fields.seller_name.value)
  expect(download).toBeDisabled()
})

it('ignores late validation after an edit even if fetch resolves after abort', async () => {
  let resolve!: (response: Response) => void
  let signal!: AbortSignal
  vi.stubGlobal('fetch', vi.fn((_url, options) => {
    signal = options.signal
    return new Promise<Response>(done => { resolve = done })
  }))
  const user = userEvent.setup()
  render(<InvoiceReview result={result} />)
  await user.click(screen.getByRole('button', { name: 'Kiểm tra dữ liệu' }))
  await user.type(screen.getByLabelText('Tổng tiền'), '0')
  expect(signal.aborted).toBe(true)
  await act(async () => { resolve(Response.json(valid)) })
  expect(screen.getByRole('button', { name: 'Xuất JSON đã xác nhận' })).toBeDisabled()
  expect(screen.queryByText('Dữ liệu hợp lệ. Có thể xuất JSON.')).not.toBeInTheDocument()
})

it('shows per-field errors and prevents invalid export', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({
    ...valid, valid: false, normalized_values: { ...valid.normalized_values, invoice_date: null },
    errors: [{ field: 'invoice_date', code: 'invalid_date', message: 'Ngày không tồn tại.' }],
  })))
  const user = userEvent.setup()
  render(<InvoiceReview result={result} />)
  await user.click(screen.getByRole('button', { name: 'Kiểm tra dữ liệu' }))
  expect(await screen.findByText('Ngày không tồn tại.')).toBeVisible()
  expect(screen.getByLabelText('Ngày hóa đơn')).toHaveAttribute('aria-invalid', 'true')
  expect(screen.getByRole('button', { name: 'Xuất JSON đã xác nhận' })).toBeDisabled()
})

it('exports normalized edits and original extraction without inventing new confidence', () => {
  const output = reviewedExport(result, { ...valid, normalized_values: {
    ...valid.normalized_values, seller_name: 'Cửa hàng đã sửa',
  } })
  expect(output.edited_fields).toEqual(['seller_name'])
  expect(output.original_extraction).toEqual(result)
  expect(output.values).not.toHaveProperty('confidence')
})

it('rejects inconsistent backend validation instead of enabling export', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({
    ...valid, normalized_values: { ...valid.normalized_values, currency: null },
  })))
  await expect(validateReviewedValues({ invoice_number: '', invoice_date: '', seller_name: '',
    total_amount: '', currency: '' })).rejects.toThrow('không nhất quán')
})

it('releases preview object URLs on file changes and unmount', () => {
  const { rerender, unmount } = render(<DocumentPreview file={new File(['one'], 'one.png')} />)
  expect(screen.getByAltText('Xem trước one.png')).toBeVisible()
  rerender(<DocumentPreview file={new File(['two'], 'two.pdf', { type: 'application/pdf' })} />)
  expect(URL.revokeObjectURL).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('Xem trước PDF')).toBeInTheDocument()
  unmount()
  expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2)
})
