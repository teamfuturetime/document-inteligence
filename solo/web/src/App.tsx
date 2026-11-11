import { useEffect, useRef, useState } from 'react'
import { call, post } from './api'
import type { Catalog, Extraction, Health, Kind, Mode, OCRProvider, Validation, Values } from './api'
import Icon from './components/Icon'
import DocumentPreview, { isPDF } from './components/DocumentPreview'
import ReviewFields from './components/ReviewFields'
import ThemeToggle from './components/ThemeToggle'

const MODES: Record<Mode, string> = { rules: 'OCR + luật', vlm: 'OCR + VLM', hybrid: 'Kết hợp OCR, luật và VLM' }
const OCR_PROVIDERS: Record<OCRProvider, string> = { tesseract: 'Tesseract local', ocrspace: 'OCR.space (API)' }

function fileSize(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MiB`
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
  const [zoom, setZoom] = useState(1)
  const [dragging, setDragging] = useState(false)
  const [showGuide, setShowGuide] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const controller = useRef<AbortController | null>(null)
  const fileInput = useRef<HTMLInputElement | null>(null)

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

  function chooseFiles(files: File[]) {
    invalidate(true)
    setZoom(1)
    setDragging(false)
    if (files.length > 1) { setFile(null); setError('Mỗi lần chỉ chọn một tài liệu.'); return }
    const next = files[0] ?? null
    if (next && next.size > 10 * 1024 * 1024) { setFile(null); setError('File vượt 10 MiB. Chọn file nhỏ hơn.'); return }
    if (next && !/\.(png|jpe?g|pdf)$/i.test(next.name) && !['image/png', 'image/jpeg', 'application/pdf'].includes(next.type)) {
      setFile(null); setError('Chọn tài liệu PNG, JPEG hoặc PDF.'); return
    }
    setFile(next)
  }

  async function loadSample() {
    invalidate(true)
    setFile(null)
    setZoom(1)
    const current = begin('Đang tải hóa đơn mẫu…')
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}samples/invoice-001.png`, { signal: current.signal })
      if (!response.ok) throw new Error('Không tải được hóa đơn mẫu. Bạn có thể chọn file khác.')
      const blob = await response.blob()
      if (!current.signal.aborted) {
        setKind('invoice')
        setFile(new File([blob], 'invoice-001.png', { type: 'image/png' }))
      }
    } catch (problem) { failed(problem, current) } finally { done(current) }
  }

  const currentStep = validation?.valid ? 3 : result ? 2 : 1
  const changedCount = result ? Object.entries(values).filter(([key, value]) => String(value ?? '') !== String(result.fields[key]?.value ?? '')).length : 0
  const statusLabel = !health ? 'Đang kết nối backend' : selectedOcr?.ready
    ? ocrProvider === 'ocrspace' ? 'API đã cấu hình' : 'OCR sẵn sàng' : 'Cần cấu hình OCR'

  return <div className="app-shell">
    <a className="skip-link" href="#workspace">Bỏ qua điều hướng</a>
    <aside className="sidebar" aria-label="Điều hướng chính">
      <a className="brand" href="#workspace" aria-label="AI-02 Solo trang chủ"><span className="brandmark"><Icon name="stack" /></span><span>AI-02 <span className="brand-solo">Solo</span></span></a>
      <div className="workspace-label"><span className="workspace-avatar">S</span><div><strong>Không gian cá nhân</strong><span>Document Intelligence</span></div><span className="workspace-key">01</span></div>
      <div className="nav-group-label">Không gian làm việc</div>
      <nav className="side-nav"><a href="#workspace" aria-label="Trích xuất tài liệu" className="nav-item active" aria-current="page"><Icon name="scan" /><span>Trích xuất tài liệu</span><Icon name="chevron" /></a>
        <button aria-label="Hướng dẫn nhanh" className={`nav-item ${showGuide ? 'selected' : ''}`} aria-expanded={showGuide} aria-controls="quick-guide" onClick={() => setShowGuide(previous => !previous)}><Icon name="help" /><span>Hướng dẫn nhanh</span></button>
      </nav>
      <div className="sidebar-facts"><div className="nav-group-label">Trong phiên này</div><div className="session-file"><Icon name="document" /><div><strong>{file ? '1 tài liệu đang mở' : 'Chưa có tài liệu'}</strong><span>{file ? `${isPDF(file) ? 'PDF' : 'Hình ảnh'} · ${fileSize(file.size)}` : 'Chọn file để bắt đầu'}</span></div></div></div>
      <div className="sidebar-bottom"><div className="scope-icon"><Icon name="shield" /></div><strong>Dữ liệu tổng hợp</strong><p>Thử nghiệm bằng hóa đơn và đơn từ mẫu của dự án.</p><span className="edition">AI-02 · Bản cá nhân</span></div>
    </aside>
    <main id="workspace" className="app-main" tabIndex={-1}>
      <header className="topbar"><div className="breadcrumb">Không gian làm việc <Icon name="chevron" /><span>Trích xuất</span></div><div className="topbar-actions"><span className="environment"><span />Bản thử nghiệm</span><ThemeToggle /></div></header>
      <div className="page-content">
        <div className="page-intro" data-enter><div><h1>Rà soát tài liệu tiếng Việt</h1><p>Trích xuất hóa đơn và đơn từ, đối chiếu từng trường rồi xuất JSON đã xác nhận.</p></div><div className={`connection ${health && selectedOcr?.ready ? 'ready' : ''}`}><span className="status-dot" /><span>{statusLabel}</span></div></div>
        {showGuide ? <section className="guide-panel" id="quick-guide" aria-labelledby="guide-title"><div><Icon name="help" /><h2 id="guide-title">Các bước xử lý</h2></div><ol><li>Chọn hóa đơn hoặc đơn đề nghị và nguồn OCR phù hợp.</li><li>Tải một tài liệu tổng hợp, rồi bấm Trích xuất dữ liệu.</li><li>Đối chiếu với bản gốc, sửa và kiểm tra dữ liệu trước khi xuất JSON.</li></ol><p>OCR.space dùng API bên ngoài. VLM cần được cấu hình riêng ở backend.</p></section> : null}
        <section className="configuration" aria-label="Cấu hình trích xuất"><div className="selectors">
          <label>Loại tài liệu<select value={kind} onChange={event => { invalidate(true); setKind(event.target.value as Kind) }}><option value="invoice">Hóa đơn bán hàng</option><option value="application">Đơn đề nghị sinh viên</option></select></label>
          <label>Nguồn OCR<select disabled={!health} value={ocrProvider} onChange={event => { invalidate(true); setOcrProvider(event.target.value as OCRProvider) }}>{Object.entries(OCR_PROVIDERS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label>Phương pháp<select value={mode} onChange={event => { invalidate(true); setMode(event.target.value as Mode) }}>{Object.entries(MODES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <button className="primary extract-button" disabled={!file || !schema || Boolean(busy) || needsVlm || !selectedOcr?.ready} onClick={extract}><Icon name="scan" />Trích xuất dữ liệu<Icon name="arrow" /></button>
        </div></section>
        {error ? <div className="notice error" role="alert"><Icon name="close" /><span>{error}</span></div> : null}
        {health && !selectedOcr?.ready ? <div className="notice"><Icon name="settings" /><span>Nguồn OCR chưa sẵn sàng. {selectedOcr?.reason ?? 'Kiểm tra cấu hình backend.'}</span></div> : null}
        {ocrProvider === 'ocrspace' ? <p className="notice"><Icon name="cloud" /><span>Tài liệu sẽ được gửi đến OCR.space. Chỉ dùng dữ liệu tổng hợp; ảnh sau tiền xử lý tối đa 1 MB. Dịch vụ không trả confidence theo từ.</span></p> : null}
        {needsVlm ? <p className="notice"><Icon name="settings" /><span>VLM chưa cấu hình. Thiết lập adapter local hoặc API theo README để dùng phương pháp này.</span></p> : null}
        <ol className="steps" aria-label="Quy trình">{['Chọn tài liệu', 'Rà soát kết quả', 'Xác nhận & xuất'].map((label, index) => <li key={label} data-state={index + 1 < currentStep || (index === 2 && validation?.valid) ? 'complete' : index + 1 === currentStep ? 'current' : 'waiting'} aria-current={index + 1 === currentStep ? 'step' : undefined}><span className="step-number">{index + 1 < currentStep || (index === 2 && validation?.valid) ? <Icon name="check" /> : `0${index + 1}`}</span><span>{label}</span>{index < 2 ? <span className="step-line" /> : null}</li>)}</ol>
        <div className="workbench">
          <section className="panel document-panel" aria-labelledby="document-title">
            <div className="panel-heading"><div><Icon name="document" /><h2 id="document-title">Tài liệu gốc</h2></div><span className="pill">Tối đa 1 trang</span></div>
            <div className="document-toolbar"><span className="document-name">{file ? <><span className={`file-type ${isPDF(file) ? 'pdf' : ''}`}>{isPDF(file) ? 'PDF' : 'IMG'}</span><span>{file.name}</span></> : <span>Chưa chọn tài liệu</span>}</span>{file ? <button className="icon-button" aria-label="Xóa tài liệu" title="Xóa tài liệu" onClick={() => chooseFiles([])}><Icon name="close" /></button> : <span className="file-formats">PNG / JPEG / PDF</span>}</div>
            <div className={`preview ${dragging ? 'is-dragging' : ''} ${file && isPDF(file) ? 'preview-pdf' : ''}`}
              onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false) }}
              onDrop={event => { event.preventDefault(); chooseFiles(Array.from(event.dataTransfer.files)) }}>
              {file ? <DocumentPreview file={file} zoom={zoom} /> : <div className="empty-preview"><div className="document-drawing" aria-hidden="true"><span className="drawing-back" /><span className="drawing-paper"><Icon name="document" /><i /><i /><i /><span>AI-02</span></span><span className="drawing-badge"><Icon name="upload" /></span></div><h3>Thêm tài liệu đầu tiên</h3><p>Chọn một file hoặc kéo thả vào đây.</p><span className="upload-limit">PNG, JPEG hoặc PDF · Tối đa 10 MiB</span></div>}
              <div className={`file-actions ${file ? 'has-file' : ''}`}><button className="file-picker" onClick={() => fileInput.current?.click()}><Icon name={file ? 'document' : 'upload'} /><span>{file ? 'Đổi tài liệu' : 'Chọn tài liệu'}</span></button><input ref={fileInput} hidden tabIndex={-1} aria-label="Tải tài liệu mẫu" type="file" accept=".png,.jpg,.jpeg,.pdf" onChange={event => { chooseFiles(Array.from(event.target.files ?? [])); event.target.value = '' }} />{!file ? <button className="sample-button" disabled={Boolean(busy)} onClick={loadSample}>Dùng hóa đơn mẫu<Icon name="arrow" /></button> : null}</div>
            </div>
            <div className="document-footer"><span><span className="status-dot" />{file ? `${fileSize(file.size)} · ${isPDF(file) ? 'Tài liệu PDF' : 'Bản xem trước ảnh'}` : 'Chỉ dùng dữ liệu mẫu hoặc tổng hợp'}</span>{file && !isPDF(file) ? <div className="zoom-controls"><button className="icon-button" aria-label="Thu nhỏ" disabled={zoom <= .75} onClick={() => setZoom(previous => Math.max(.75, previous - .25))}><Icon name="minus" /></button><output aria-label="Mức phóng to">{Math.round(zoom * 100)}%</output><button className="icon-button" aria-label="Phóng to" disabled={zoom >= 1.75} onClick={() => setZoom(previous => Math.min(1.75, previous + .25))}><Icon name="plus" /></button><button className="icon-button" aria-label="Vừa khung" onClick={() => setZoom(1)}><Icon name="fit" /></button></div> : null}</div>
          </section>
          <section className="panel review-panel" aria-labelledby="review-title">
            <div className="panel-heading"><div><Icon name="scan" /><h2 id="review-title">Kết quả trích xuất</h2></div><span className={`pill ${result ? 'mint' : ''}`}>{result ? `${filled}/${schema?.fields.length} trường` : 'Chờ xử lý'}</span></div>
            {busy ? <p className="busy-message" role="status"><span className="spinner" />{busy}</p> : null}
            {!result ? <div className="empty-review"><div className="review-empty-heading"><span className="empty-scan"><Icon name="scan" /></span><h3>Đối chiếu trước khi xuất</h3><p>Các trường được đọc từ tài liệu sẽ xuất hiện ở đây để bạn kiểm tra và chỉnh sửa.</p></div><div className="empty-fields" aria-hidden="true">{(schema?.fields ?? []).map((definition, index) => <div className="empty-field" key={definition.key}><span>{definition.label}</span><i style={{ width: `${[68, 45, 80, 55, 30][index % 5]}%` }} /></div>)}</div><div className="review-note"><Icon name="shield" /><span>JSON chỉ được xuất sau khi dữ liệu đã được kiểm tra hợp lệ.</span></div></div> : <>
              <div className="result-summary"><span>{schema?.title}</span><span className="result-source"><Icon name={resultOcr === 'ocrspace' ? 'cloud' : 'server'} />{resultOcr ? OCR_PROVIDERS[resultOcr] : 'OCR'} · {MODES[result.mode]}</span><p>{resultOcr === 'ocrspace' ? 'OCR.space không cung cấp confidence; hãy kiểm tra bằng chứng và ảnh.' : 'Confidence là tín hiệu OCR gốc, chưa được hiệu chuẩn thành xác suất đúng.'}</p></div>
              {result.warnings.map((warning, index) => <p className="notice result-warning" key={index}>{warning}</p>)}
              {schema ? <ReviewFields schema={schema} result={result} values={values} errors={validation?.errors} onChange={(key, value) => { invalidate(); setValues(previous => ({ ...previous, [key]: value })) }} /> : null}
              <div className="review-completion"><span>{changedCount ? `${changedCount} trường đã chỉnh sửa` : 'Đối chiếu từng trường với bản gốc'}</span>{validation?.valid ? <span className="validated"><Icon name="check" />Đã kiểm tra</span> : <span>Chưa xác nhận</span>}</div>
              <div className="review-actions"><button disabled={Boolean(busy)} onClick={validate}><Icon name="check" />Kiểm tra dữ liệu</button><button className="primary" disabled={!validation?.valid || Boolean(busy)} onClick={download}><Icon name="download" />Xuất JSON đã xác nhận</button></div>
              {validation ? <p role="status" className={validation.valid ? 'valid-message' : 'validation-message'}>{validation.valid ? 'Dữ liệu hợp lệ. Hãy xác nhận đã đối chiếu tài liệu trước khi tải JSON.' : 'Cần sửa các trường được đánh dấu rồi kiểm tra lại.'}</p> : <p className="footnote">Kiểm tra dữ liệu để mở quyền xuất JSON.</p>}
              <details className="technical"><summary><Icon name="code" />Nội dung OCR & phiên bản xử lý<Icon name="chevron" /></summary><pre>{result.ocr_text}</pre><pre>{JSON.stringify(result.provenance, null, 2)}</pre></details>
            </>}
          </section>
        </div>
        <footer className="app-footer"><span>AI-02 Solo <span className="footer-divider">/</span> Document Intelligence</span><span><Icon name="shield" />Dữ liệu mẫu & tổng hợp</span></footer>
      </div>
    </main>
  </div>
}
