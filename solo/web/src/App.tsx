import { useEffect, useRef, useState } from 'react'
import { call, post } from './api'
import type { Catalog, Extraction, Health, Kind, Mode, OCRProvider, Validation, Values } from './api'

const MODES: Record<Mode, string> = { rules: 'OCR + luật', vlm: 'OCR + VLM', hybrid: 'Kết hợp OCR, luật và VLM' }
const OCR_PROVIDERS: Record<OCRProvider, string> = { tesseract: 'Tesseract local', ocrspace: 'OCR.space (API)' }
const SOURCES: Record<string, string> = { rules: 'Luật theo nhãn', vlm: 'Mô hình thị giác–ngôn ngữ', agreement: 'Hai nguồn đồng ý', conflict: 'Cần quyết định', missing: 'Chưa xác định' }

function Preview({ file }: { file: File }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    const next = URL.createObjectURL(file)
    setUrl(next)
    return () => URL.revokeObjectURL(next)
  }, [file])
  if (!url) return null
  return file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
    ? <object data={url} type="application/pdf" aria-label="Bản xem trước PDF"><a href={url} download={file.name}>Tải PDF để đối chiếu</a></object>
    : <img src={url} alt={`Bản xem trước ${file.name}`} />
}

export default function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [kind, setKind] = useState<Kind>('invoice')
  const [mode, setMode] = useState<Mode>('rules')
  const [ocrProvider, setOcrProvider] = useState<OCRProvider>('tesseract')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<Extraction | null>(null)
  const [values, setValues] = useState<Values>({})
  const [validation, setValidation] = useState<Validation | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const controller = useRef<AbortController | null>(null)

  useEffect(() => {
    const initial = new AbortController()
    Promise.all([call<Catalog>('/api/schemas', { signal: initial.signal }), call<Health>('/health', { signal: initial.signal })])
      .then(([schemas, status]) => { if (!initial.signal.aborted) { setCatalog(schemas); setHealth(status); if (status.ocr.provider) setOcrProvider(status.ocr.provider) } })
      .catch(() => { if (!initial.signal.aborted) setError('Không kết nối được backend. Kiểm tra server ở cổng 8100 rồi tải lại trang.') })
    return () => { initial.abort(); controller.current?.abort() }
  }, [])

  function invalidate(clearResult = false) {
    controller.current?.abort()
    controller.current = null
    setValidation(null); setError(''); setBusy('')
    if (clearResult) { setResult(null); setValues({}) }
  }

  function begin(label: string) {
    controller.current?.abort()
    const next = new AbortController()
    controller.current = next
    setBusy(label); setError('')
    return next
  }

  function failed(problem: unknown, current: AbortController) {
    if (!current.signal.aborted) setError(problem instanceof Error ? problem.message : 'Không xử lý được request.')
  }

  function done(current: AbortController) {
    if (controller.current === current) setBusy('')
  }

  async function extract() {
    if (!file) return
    invalidate(true)
    const current = begin('Đang nhận diện tài liệu…')
    try {
      const body = new FormData()
      body.set('document_type', kind); body.set('mode', mode); body.set('file', file)
      body.set('ocr_provider', ocrProvider)
      const response = await call<Extraction>('/api/extract', { method: 'POST', body, signal: current.signal })
      if (!current.signal.aborted) {
        if (response.document_type !== kind || response.schema_version !== 'solo-1.0' || !response.fields) throw new Error('Response không khớp schema tài liệu.')
        setResult(response)
        setValues(Object.fromEntries(Object.entries(response.fields).map(([key, field]) => [key, field.value ?? ''])))
      }
    } catch (problem) { failed(problem, current) } finally { done(current) }
  }

  async function validate() {
    setValidation(null)
    const current = begin('Đang kiểm tra dữ liệu…')
    try {
      const response = await post<Validation>('/api/validate', { document_type: kind, values }, current.signal)
      if (!current.signal.aborted) setValidation(response)
    } catch (problem) { failed(problem, current) } finally { done(current) }
  }

  async function download() {
    if (!result || !validation?.valid) return
    const current = begin('Đang tạo JSON…')
    try {
      // Server revalidates this exact snapshot even after browser validation.
      const response = await post<unknown>('/api/export', { original: result, values }, current.signal)
      if (current.signal.aborted) return
      const url = URL.createObjectURL(new Blob([JSON.stringify(response, null, 2) + '\n'], { type: 'application/json' }))
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = `ai02-${kind}-reviewed.json`
      document.body.append(anchor); anchor.click(); anchor.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (problem) { failed(problem, current) } finally { done(current) }
  }

  const schema = catalog?.[kind]
  const needsVlm = mode !== 'rules' && !health?.vlm.configured
  const selectedOcr = health?.ocr_providers?.[ocrProvider] ?? (ocrProvider === 'tesseract' ? health?.ocr : undefined)
  const resultOcr = (result?.provenance.ocr as { provider?: OCRProvider } | undefined)?.provider
  const filled = result ? Object.values(result.fields).filter(field => field.value !== null).length : 0

  return <>
    <header className="topbar"><a className="brand" href="/" aria-label="AI-02 Solo trang chủ"><span className="brandmark">S</span><span>AI-02 <strong>Solo</strong></span></a><span className="local-tag">Bản cá nhân · Dữ liệu tổng hợp</span></header>
    <main>
      <section className="intro"><p className="eyebrow">DOCUMENT INTELLIGENCE / TIẾNG VIỆT</p><h1>Từ tài liệu đến dữ liệu<br /><span>đã được bạn xác nhận.</span></h1><p>Tải mẫu hóa đơn hoặc đơn từ, đối chiếu kết quả nhận diện và hoàn thiện từng trường trước khi xuất JSON.</p></section>
      <ol className="steps" aria-label="Quy trình"><li className="active"><b>01</b> Chọn tài liệu</li><li className={result ? 'active' : ''}><b>02</b> Rà soát & sửa</li><li className={validation?.valid ? 'active' : ''}><b>03</b> Xác nhận & xuất</li></ol>
      {error ? <div className="notice error" role="alert">{error}</div> : null}
      {health && !selectedOcr?.ready ? <div className="notice">Nguồn OCR chưa sẵn sàng. {selectedOcr?.reason ?? 'Kiểm tra cấu hình backend.'}</div> : null}
      <div className="workspace">
        <section className="panel document-panel" aria-labelledby="document-title">
          <div className="panel-heading"><div><p className="eyebrow">TÀI LIỆU GỐC</p><h2 id="document-title">Chọn mẫu để bắt đầu</h2></div><span className="pill">01 trang</span></div>
          <div className="selectors"><label>Loại tài liệu<select value={kind} onChange={event => { invalidate(true); setKind(event.target.value as Kind) }}><option value="invoice">Hóa đơn bán hàng</option><option value="application">Đơn đề nghị sinh viên</option></select></label><label>Nguồn OCR<select disabled={!health} value={ocrProvider} onChange={event => { invalidate(true); setOcrProvider(event.target.value as OCRProvider) }}>{Object.entries(OCR_PROVIDERS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><label>Phương pháp<select value={mode} onChange={event => { invalidate(true); setMode(event.target.value as Mode) }}>{Object.entries(MODES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label></div>
          {ocrProvider === 'ocrspace' ? <p className="notice">Tài liệu sẽ được gửi đến OCR.space. Chỉ dùng dữ liệu tổng hợp; ảnh sau tiền xử lý tối đa 1 MB. Dịch vụ không trả confidence theo từ.</p> : null}
          {needsVlm ? <p className="notice">VLM chưa cấu hình. Thiết lập adapter local hoặc API theo README để dùng phương pháp này.</p> : null}
          <label className="file-picker"><span className="upload-icon" aria-hidden="true">↑</span><strong>{file ? file.name : 'Chọn một tài liệu mẫu'}</strong><span>PNG, JPEG hoặc PDF · Tối đa 10 MiB</span><input aria-label="Tải tài liệu mẫu" type="file" accept=".png,.jpg,.jpeg,.pdf" onChange={event => {
            invalidate(true)
            const next = event.target.files?.[0] ?? null
            if (next && next.size > 10 * 1024 * 1024) { setFile(null); setError('File vượt 10 MiB. Chọn file nhỏ hơn.'); return }
            setFile(next)
          }} /></label>
          <button className="primary full" disabled={!file || !schema || Boolean(busy) || needsVlm || !selectedOcr?.ready} onClick={extract}>Trích xuất dữ liệu <span aria-hidden="true">↗</span></button>
          <div className="preview">{file ? <Preview key={`${file.name}-${file.lastModified}`} file={file} /> : <div className="empty-preview"><div className="paper-icon" aria-hidden="true">▤</div><p>Bản xem trước tài liệu</p><small>Chỉ dùng dữ liệu mẫu hoặc dữ liệu tổng hợp.</small></div>}</div>
        </section>
        <section className="panel review-panel" aria-labelledby="review-title">
          <div className="panel-heading"><div><p className="eyebrow">DỮ LIỆU CÓ CẤU TRÚC</p><h2 id="review-title">Rà soát kết quả</h2></div><span className="pill">{result ? `${filled}/${schema?.fields.length} trường` : 'Chờ tài liệu'}</span></div>
          {busy ? <p className="notice" role="status">{busy}</p> : null}
          {!result ? <div className="empty-review"><span className="review-symbol" aria-hidden="true">✓</span><h3>Mỗi trường, một lần kiểm tra.</h3><p>Kết quả AI sẽ xuất hiện tại đây. Bạn luôn có thể đối chiếu bằng chứng và sửa lại trước khi xuất dữ liệu.</p></div> : <>
            <p className="result-summary">{schema?.title} · {resultOcr ? OCR_PROVIDERS[resultOcr] : 'OCR'} · {MODES[result.mode]}<br /><small>{resultOcr === 'ocrspace' ? 'OCR.space không cung cấp confidence; hãy kiểm tra bằng chứng và ảnh.' : 'Confidence là tín hiệu OCR, chưa được hiệu chuẩn thành xác suất đúng.'}</small></p>
            {result.warnings.map((warning, index) => <p className="notice" key={index}>{warning}</p>)}
            <div className="fields">{schema?.fields.map(definition => {
              const extracted = result.fields[definition.key]
              const changed = String(values[definition.key] ?? '') !== String(extracted.value ?? '')
              return <div className="field" key={definition.key}><div className="field-heading"><label htmlFor={definition.key}>{definition.label}</label><span className={extracted.confidence === null || extracted.confidence < .75 ? 'confidence low' : 'confidence'}>{extracted.confidence === null ? 'Chưa có confidence' : `OCR gốc ${Math.round(extracted.confidence * 100)}%`}</span></div>
                <input id={definition.key} type={definition.type} value={values[definition.key] ?? ''} aria-invalid={Boolean(validation?.errors[definition.key])} aria-describedby={`${definition.key}-help`} onChange={event => { invalidate(); setValues(previous => ({ ...previous, [definition.key]: event.target.value })) }} />
                <div id={`${definition.key}-help`} className="field-help">{changed ? <span className="edited">Bạn đã chỉnh sửa · confidence chỉ thuộc kết quả AI gốc</span> : <span>{SOURCES[extracted.source]}</span>}{validation?.errors[definition.key] ? <p className="field-error">{validation.errors[definition.key]}</p> : null}</div>
                {extracted.warnings.map((warning, index) => <p className="field-warning" key={index}>{warning}</p>)}
                <details><summary>Bằng chứng OCR ({extracted.evidence.length})</summary>{extracted.evidence.length ? extracted.evidence.map((item, index) => <blockquote key={index}>{item}</blockquote>) : <p>Chưa có bằng chứng OCR cho trường này. Đối chiếu ảnh gốc.</p>}</details>
              </div>
            })}</div>
            <div className="review-actions"><button disabled={Boolean(busy)} onClick={validate}>Kiểm tra dữ liệu</button><button className="primary" disabled={!validation?.valid || Boolean(busy)} onClick={download}>Xuất JSON đã xác nhận ↓</button></div>
            {validation ? <p role="status" className={validation.valid ? 'valid-message' : 'field-error'}>{validation.valid ? 'Dữ liệu hợp lệ. Hãy xác nhận đã đối chiếu tài liệu trước khi tải JSON.' : 'Cần sửa các trường được đánh dấu rồi kiểm tra lại.'}</p> : <p className="footnote">Xuất JSON được mở sau khi tất cả trường hợp lệ.</p>}
            <details className="technical"><summary>Nội dung OCR & phiên bản xử lý</summary><pre>{result.ocr_text}</pre><pre>{JSON.stringify(result.provenance, null, 2)}</pre></details>
          </>}
        </section>
      </div>
      <footer>AI-02 Solo <span>OCR → Trích xuất → Rà soát → JSON</span></footer>
    </main>
  </>
}
