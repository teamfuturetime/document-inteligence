import { describe, expect, it } from 'vitest'
import { MAX_FILE_BYTES, validateFileSelection } from './fileSelection'

describe('local file selection', () => {
  it.each([['sample.png', 'image/png'], ['sample.JPG', 'image/jpeg'], ['sample.pdf', 'application/pdf']])(
    'accepts %s', (name, type) => {
      expect(validateFileSelection(new File(['synthetic'], name, { type }))).toBeNull()
    },
  )
  it('accepts known extensions when browser omits MIME', () => {
    expect(validateFileSelection(new File(['synthetic'], 'sample.jpeg'))).toBeNull()
  })
  it('rejects empty files', () => {
    expect(validateFileSelection(new File([], 'sample.pdf'))).toContain('rỗng')
  })
  it('rejects unsupported or mismatched types', () => {
    expect(validateFileSelection(new File(['data'], 'sample.txt'))).toContain('Chỉ hỗ trợ')
    expect(validateFileSelection(new File(['data'], 'sample.png', { type: 'text/plain' }))).toContain('không được hỗ trợ')
  })
  it('accepts exactly the size limit and rejects one byte more', () => {
    expect(validateFileSelection(new File([new Uint8Array(MAX_FILE_BYTES)], 'sample.pdf'))).toBeNull()
    expect(validateFileSelection(new File([new Uint8Array(MAX_FILE_BYTES + 1)], 'sample.pdf'))).toContain('10 MiB')
  })
})
