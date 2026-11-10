import {describe, expect, it} from 'vitest'
import {extractedFieldLabel, extractionNotice} from './extractedFields'

describe('extracted fields presentation', () => {
  it('labels machine field keys and retains arbitrary human-created fields', () => {
    expect(extractedFieldLabel('invoice_number')).toBe('Số hóa đơn')
    expect(extractedFieldLabel('nationality')).toBe('Quốc tịch')
    expect(extractedFieldLabel('form_name')).toBe('Tên biểu mẫu')
    expect(extractedFieldLabel('Trường nhập tay')).toBe('Trường nhập tay')
  })
  it('distinguishes pending machine results, saved review and confirmation', () => {
    expect(extractionNotice('pending_review')).toContain('máy trích xuất')
    expect(extractionNotice('reviewed')).toContain('chưa được xác nhận')
    expect(extractionNotice('confirmed')).toBe('Dữ liệu đã được người dùng xác nhận.')
    expect(extractionNotice('pending_review', 'manual')).toContain('nhập thủ công')
  })
})
