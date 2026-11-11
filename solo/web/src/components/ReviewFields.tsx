import type { Extraction, Schema, Values } from '../api'
import Icon from './Icon'

const SOURCES: Record<string, string> = {
  rules: 'Đọc theo nhãn trong tài liệu', vlm: 'Mô hình thị giác–ngôn ngữ', agreement: 'OCR và VLM thống nhất',
  conflict: 'Hai nguồn chưa thống nhất', missing: 'Cần bổ sung từ bản gốc',
}

interface Props {
  schema: Schema
  result: Extraction
  values: Values
  errors?: Record<string, string>
  onChange: (key: string, value: string) => void
}

export default function ReviewFields({ schema, result, values, errors, onChange }: Props) {
  return <div className="fields">{schema.fields.map(definition => {
    const extracted = result.fields[definition.key]
    const changed = String(values[definition.key] ?? '') !== String(extracted.value ?? '')
    const hasError = Boolean(errors?.[definition.key])
    return <div className={`field ${hasError ? 'has-error' : ''}`} key={definition.key}>
      <div className="field-heading">
        <label htmlFor={definition.key}>{definition.label}</label>
        <span className={`confidence ${extracted.confidence === null ? 'unknown' : extracted.confidence < .75 ? 'low' : ''}`}>
          {extracted.confidence === null ? 'Chưa có confidence' : <><span className="confidence-dot" />OCR gốc {Math.round(extracted.confidence * 100)}%</>}
        </span>
      </div>
      <input id={definition.key} type={definition.type} inputMode={definition.key === 'total_amount' ? 'numeric' : undefined}
        autoComplete="off" value={values[definition.key] ?? ''} aria-invalid={hasError}
        aria-describedby={`${definition.key}-help`} onChange={event => onChange(definition.key, event.target.value)} />
      <div id={`${definition.key}-help`} className="field-help">
        {changed ? <span className="edited"><Icon name="check" />Bạn đã chỉnh sửa · {extracted.confidence === null ? 'kết quả gốc không có confidence' : 'confidence chỉ thuộc kết quả AI gốc'}</span>
          : <span>{SOURCES[extracted.source]}</span>}
        {hasError ? <p className="field-error">{errors?.[definition.key]}</p> : null}
        {extracted.warnings.map((warning, index) => <p className="field-warning" key={index}>{warning}</p>)}
      </div>
      <details className="evidence"><summary><Icon name="chevron" />Bằng chứng OCR <span>{extracted.evidence.length}</span></summary>
        {extracted.evidence.length ? extracted.evidence.map((item, index) => <blockquote key={index}>{item}</blockquote>) : <p>Chưa có bằng chứng OCR. Đối chiếu trường này với tài liệu gốc.</p>}
      </details>
    </div>
  })}</div>
}
