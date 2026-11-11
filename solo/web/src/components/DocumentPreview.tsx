import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'

export function isPDF(file: File) {
  return file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
}

export default function DocumentPreview({ file, zoom }: { file: File; zoom: number }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    const next = URL.createObjectURL(file)
    setUrl(next)
    return () => URL.revokeObjectURL(next)
  }, [file])
  if (!url) return null
  if (isPDF(file)) return <object className="pdf-preview" data={url} type="application/pdf" aria-label="Bản xem trước PDF"><a href={url} download={file.name}>Tải PDF để đối chiếu</a></object>
  return <div className="preview-sheet" style={{ '--document-zoom': zoom } as CSSProperties}>
    <img src={url} alt={`Bản xem trước ${file.name}`} />
  </div>
}
