import type { ExtractionResponse } from '../../api/generated/extraction-response'

const labels = {
  invoice_number: 'Số hóa đơn', invoice_date: 'Ngày hóa đơn',
  seller_name: 'Bên bán', total_amount: 'Tổng tiền', currency: 'Tiền tệ',
} as const

export function ExtractionResult({ result }: { result: ExtractionResponse }) {
  return (
    <section className="result" aria-label="Kết quả trích xuất">
      <h3>{result.mode === 'mock' ? 'Kết quả mock — chưa chạy OCR' : 'Kết quả trích xuất'}</h3>
      {result.mode === 'mock' ? <p className="note">Dữ liệu mẫu cố định, không được suy ra từ tài liệu bạn vừa gửi.</p> : null}
      <dl>
        {(Object.keys(labels) as Array<keyof typeof labels>).map(key => (
          <div key={key}>
            <dt>{labels[key]}</dt>
            <dd>{result.fields[key].value === null ? 'Chưa tìm thấy' : String(result.fields[key].value)}</dd>
          </div>
        ))}
      </dl>
      <p className="hint">OCR: {result.ocr_version} · Schema: {result.schema_version}</p>
      <p className="hint">{result.mode === 'mock' ? 'Chưa có confidence hoặc evidence từ OCR thật.' : 'Kết quả cần được review.'}</p>
    </section>
  )
}
