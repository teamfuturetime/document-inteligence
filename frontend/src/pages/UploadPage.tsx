import { useState, type DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadCloud } from 'lucide-react'
import { api } from '../api/client'
import { validateUpload } from '../utils/files'

export default function UploadPage() {
  const [file, setFile] = useState<File>()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  function choose(candidate?: File) {
    setError('')
    if (!candidate) return
    const issue = validateUpload(candidate)
    if (issue) return setError(issue)
    setFile(candidate)
  }

  async function submit() {
    if (!file) return
    setBusy(true)
    try {
      const document = await api.upload(file)
      await api.process(document.id)
      navigate('/documents/' + document.id)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Không thể xử lý tài liệu')
      setBusy(false)
    }
  }

  function drop(event: DragEvent) {
    event.preventDefault()
    choose(event.dataTransfer.files[0])
  }

  return <>
    <div className="page-title"><div><h1>Tải tài liệu</h1><p>Hỗ trợ PDF, PNG và JPEG, tối đa 10 MB.</p></div></div>
    <div className="card mx-auto max-w-3xl p-6">
      <label onDrop={drop} onDragOver={event => event.preventDefault()} className="flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 text-center hover:border-blue-400">
        <UploadCloud size={42} className="text-blue-600"/><strong className="mt-4">Kéo thả file vào đây</strong><span className="mt-1 text-sm text-slate-500">hoặc bấm để chọn file</span>
        <input className="hidden" type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={event => choose(event.target.files?.[0])}/>
      </label>
      {file && <div className="mt-4 rounded-lg bg-blue-50 p-4"><b>{file.name}</b><div className="text-sm text-slate-500">{(file.size/1024/1024).toFixed(2)} MB</div></div>}
      {error && <div className="error mt-4">{error}</div>}
      <button disabled={!file || busy} onClick={submit} className="button-primary mt-5 w-full">{busy ? 'AI đang xử lý, vui lòng chờ…' : 'Tải lên và xử lý'}</button>
      {busy && <div className="mt-3 h-1.5 overflow-hidden rounded bg-slate-200"><div className="indeterminate h-full bg-blue-600"/></div>}
    </div>
  </>
}
