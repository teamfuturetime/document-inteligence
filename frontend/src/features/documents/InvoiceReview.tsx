import { useEffect, useRef, useState } from 'react'
import { fieldLabels, invoiceFields, reviewedExport, validateReviewedValues } from '../../api/client'
import type { ExtractionResponse } from '../../api/generated/extraction-response'
import type { ValidationResponse } from '../../api/generated/validation-response'

function initialValues(result: ExtractionResponse) {
  return Object.fromEntries(invoiceFields.map(field => [field,
    result.fields[field].value === null ? '' : String(result.fields[field].value),
  ])) as Record<keyof typeof fieldLabels, string>
}

export function InvoiceReview({ result }: { result: ExtractionResponse }) {
  const [values, setValues] = useState(() => initialValues(result))
  const [validation, setValidation] = useState<ValidationResponse | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const request = useRef<AbortController | null>(null)
  useEffect(() => () => request.current?.abort(), [])

  function invalidate() {
    request.current?.abort()
    setValidation(null)
    setError(null)
    setPending(false)
  }

  async function validate() {
    invalidate()
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    try {
      const response = await validateReviewedValues(values, controller.signal)
      if (!controller.signal.aborted) setValidation(response)
    } catch (issue) {
      if (!controller.signal.aborted) setError(issue instanceof Error ? issue.message : 'Không thể validation.')
    } finally {
      if (!controller.signal.aborted) setPending(false)
    }
  }

  function download() {
    if (!validation?.valid || pending) return
    try {
      const output = reviewedExport(result, validation)
      const url = URL.createObjectURL(new Blob([JSON.stringify(output, null, 2) + '\n'], { type: 'application/json;charset=utf-8' }))
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'invoice-reviewed.json'
      document.body.append(anchor)
      anchor.click()
      anchor.remove()
      setTimeout(() => URL.revokeObjectURL(url), 0)
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : 'Không thể xuất JSON.')
    }
  }

  return <section className="review" aria-labelledby="review-heading">
    <h3 id="review-heading">Kiểm tra và chỉnh sửa</h3>
    <p className="hint">Đối chiếu tài liệu gốc. Nhập ngày ISO YYYY-MM-DD và tổng tiền VND.</p>
    <form onSubmit={event => { event.preventDefault(); void validate() }}>
      {invoiceFields.map(field => {
        const errors = validation?.errors.filter(error => error.field === field) ?? []
        const source = result.fields[field]
        return <div className="review-field" key={field}>
          <label htmlFor={`review-${field}`}>{fieldLabels[field]}</label>
          <input id={`review-${field}`} value={values[field]} maxLength={1000}
            inputMode={field === 'total_amount' ? 'numeric' : undefined}
            aria-invalid={errors.length > 0} aria-describedby={`review-help-${field}`}
            onChange={event => {
              const value = event.currentTarget.value
              invalidate()
              setValues(current => ({ ...current, [field]: value }))
            }} />
          <div id={`review-help-${field}`} className="hint">
            <span>Confidence AI gốc: {source.confidence === null ? 'không xác định' : `${(source.confidence * 100).toFixed(1)}%`}</span>
            {source.warnings.length ? <span> · Cảnh báo: {source.warnings.join(', ')}</span> : null}
            {errors.map(error => <p className="field-error" key={error.code}>{error.message}</p>)}
          </div>
          {source.evidence.length ? <details><summary>Evidence OCR ({source.evidence.length} token)</summary>
            <ul>{source.evidence.map((item, index) => <li key={index}>{item.text} <small>· trang {item.page}, box processed [{item.box.x0}, {item.box.y0}, {item.box.x1}, {item.box.y1}]</small></li>)}</ul>
          </details> : null}
        </div>
      })}
      <div className="actions">
        <button type="submit" disabled={pending}>{pending ? 'Đang kiểm tra dữ liệu…' : 'Kiểm tra dữ liệu'}</button>
        <button type="button" className="secondary" onClick={() => { invalidate(); setValues(initialValues(result)) }}>Khôi phục kết quả gốc</button>
        <button type="button" onClick={download} disabled={!validation?.valid || pending}>Xuất JSON đã xác nhận</button>
      </div>
    </form>
    <div aria-live="polite">
      {error ? <p role="alert" className="error">{error}</p> : null}
      {validation ? <p className={validation.valid ? 'success' : 'error'} role={validation.valid ? 'status' : 'alert'}>
        {validation.valid ? 'Dữ liệu hợp lệ. Có thể xuất JSON.' : 'Cần sửa các trường được đánh dấu trước khi xuất.'}
      </p> : <p className="hint">Chưa kiểm tra bản chỉnh sửa hiện tại.</p>}
    </div>
    <p className="hint">Bản xuất giữ nguyên kết quả AI gốc, mode/version và danh sách trường đã sửa; không gán confidence AI cho giá trị bạn sửa.</p>
  </section>
}
