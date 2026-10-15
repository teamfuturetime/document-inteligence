import { useEffect, useState } from 'react'

export function DocumentPreview({ file }: { file: File }) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    const objectURL = URL.createObjectURL(file)
    setUrl(objectURL)
    return () => URL.revokeObjectURL(objectURL)
  }, [file])
  if (!url) return null
  const pdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  return <figure className="preview">
    <figcaption>Tài liệu gốc · {file.name}</figcaption>
    {pdf ? <object data={url} type="application/pdf" aria-label="Xem trước PDF" width="100%" height="500">
      <p>Trình duyệt không hỗ trợ xem PDF tại đây.</p>
    </object> : <img src={url} alt={`Xem trước ${file.name}`} />}
    <a href={url} download={file.name}>Tải tài liệu gốc để đối chiếu</a>
  </figure>
}
