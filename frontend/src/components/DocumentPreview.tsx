import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Document } from '../types'

export default function DocumentPreview({ document }: { document: Document }) {
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(1)
  const [src, setSrc] = useState('')
  const [error, setError] = useState('')
  const converted = /\.(bmp|tiff?)$/i.test(document.filename)

  useEffect(() => {
    if (!converted) return
    const controller = new AbortController()
    let url = ''
    setSrc('')
    setError('')
    void (async () => {
      try {
        const response = await fetch(api.preview(document.id) + '?page=' + page, {
          credentials: 'include', signal: controller.signal,
        })
        if (!response.ok) throw new Error('Không thể tải bản xem trước.')
        const blob = await response.blob()
        if (controller.signal.aborted) return
        url = URL.createObjectURL(blob)
        setCount(Number(response.headers.get('X-Page-Count')) || 1)
        setSrc(url)
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Không thể tải bản xem trước.')
      }
    })()
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url) }
  }, [converted, document.id, page])

  if (document.content_type === 'application/pdf') {
    return <iframe title="Xem PDF" className="h-[70vh] w-full" src={api.preview(document.id)} />
  }
  return <>
    {converted && count > 1 && <nav aria-label="Trang xem trước" className="flex items-center justify-center gap-3 border-b p-3">
      <button className="button-subtle" disabled={page === 1} onClick={() => setPage(value => value - 1)}>Trang trước</button>
      <span>Trang {page} / {count}</span>
      <button className="button-subtle" disabled={page === count} onClick={() => setPage(value => value + 1)}>Trang sau</button>
    </nav>}
    <div className="grid min-h-96 place-items-center bg-slate-100 p-4">
      {error ? <p role="alert">{error}</p> : converted && !src ? <p>Đang tải bản xem trước…</p> :
        <img className="max-h-[70vh]" src={converted ? src : api.preview(document.id)} alt={document.filename} />}
    </div>
  </>
}
