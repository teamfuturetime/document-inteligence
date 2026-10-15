import { useEffect, useRef, useState } from 'react'
import { uploadDocument } from '../../api/client'
import type { ExtractionResponse } from '../../api/generated/extraction-response'
import { ExtractionResult } from './ExtractionResult'
import { validateFileSelection } from './fileSelection'
import { DocumentPreview } from './DocumentPreview'

export function DocumentSelection() {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [upload, setUpload] = useState<
    { status: 'idle' | 'loading' } | { status: 'complete'; result: ExtractionResponse }
  >({ status: 'idle' })
  const request = useRef<AbortController | null>(null)
  useEffect(() => () => { request.current?.abort() }, [])

  function resetUpload() {
    request.current?.abort()
    setUpload({ status: 'idle' })
  }

  async function sendDocument() {
    if (!file) return
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setUpload({ status: 'loading' })
    setError(null)
    try {
      const result = await uploadDocument(file, controller.signal)
      if (!controller.signal.aborted) setUpload({ status: 'complete', result })
    } catch (issue) {
      if (!controller.signal.aborted) {
        setUpload({ status: 'idle' })
        setError(issue instanceof Error ? issue.message : 'Không thể upload tài liệu.')
      }
    }
  }

  return (
    <section className="panel" aria-labelledby="document-heading">
      <span className="step">01 / TÀI LIỆU</span>
      <h2 id="document-heading">Chuẩn bị hóa đơn mẫu</h2>
      <p>Gửi hóa đơn synthetic để OCR, trích xuất và đối chiếu kết quả.</p>
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
          resetUpload()
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
          <span>{(file.size / 1024).toFixed(1)} KiB · {upload.status === 'complete' ? 'Đã gửi lên server' : upload.status === 'loading' ? 'Đang gửi' : 'Chưa gửi lên server'}</span>
          <button onClick={sendDocument} disabled={upload.status === 'loading'}>
            {upload.status === 'loading' ? 'Đang gửi…' : 'Trích xuất hóa đơn'}
          </button>
          <button className="secondary" onClick={() => { resetUpload(); setFile(null); setError(null) }}>Bỏ chọn</button>
        </div>
      ) : <p className="empty">Chưa chọn tài liệu.</p>}
      {file ? <DocumentPreview key={`${file.name}-${file.lastModified}`} file={file} /> : null}
      <div aria-live="polite" aria-busy={upload.status === 'loading'}>
        {upload.status === 'complete' ? <ExtractionResult result={upload.result} /> : null}
      </div>
      <p className="note">Kết quả OCR cần được kiểm tra. Nếu server chạy mock, kết quả sẽ được gắn nhãn rõ.</p>
    </section>
  )
}
