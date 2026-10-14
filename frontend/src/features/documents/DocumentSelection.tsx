import { useState } from 'react'
import { validateFileSelection } from './fileSelection'

export function DocumentSelection() {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  return (
    <section className="panel" aria-labelledby="document-heading">
      <span className="step">01 / TÀI LIỆU</span>
      <h2 id="document-heading">Chuẩn bị hóa đơn mẫu</h2>
      <p>Chọn tài liệu synthetic để chuẩn bị cho bước xử lý tiếp theo.</p>
      <label className="file-label" htmlFor="document">Chọn PNG, JPG hoặc PDF</label>
      <input
        id="document"
        type="file"
        accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf"
        aria-describedby="document-help"
        aria-invalid={Boolean(error)}
        onChange={event => {
          const selected = event.target.files?.[0]
          if (!selected) return
          const issue = validateFileSelection(selected)
          setError(issue)
          setFile(issue ? null : selected)
          // Allows choosing the same file again after an error or a reset.
          event.target.value = ''
        }}
      />
      <p id="document-help" className="hint">Tối đa 10 MiB, một trang. Chỉ dùng dữ liệu giả.</p>
      {error ? <p role="alert" className="error">{error}</p> : null}
      {file ? (
        <div className="selected-file" role="status">
          <strong>{file.name}</strong>
          <span>{(file.size / 1024).toFixed(1)} KiB · Chưa gửi lên server</span>
          <button className="secondary" onClick={() => { setFile(null); setError(null) }}>Bỏ chọn</button>
        </div>
      ) : <p className="empty">Chưa chọn tài liệu.</p>}
      <p className="note">Bước xử lý và trích xuất sẽ được bổ sung ở task demo tiếp theo.</p>
    </section>
  )
}
