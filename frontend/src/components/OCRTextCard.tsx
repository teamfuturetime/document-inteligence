import {useState} from 'react'

type OCRTextCardProps={
  cleanedText?:string|null
  rawText?:string|null
}

export default function OCRTextCard({cleanedText,rawText}:OCRTextCardProps){
  const [copied,setCopied]=useState(false)
  const readableText=cleanedText?.trim()||rawText?.trim()||''
  const raw=rawText?.trim()||''

  async function copyText(){
    if(!readableText)return
    try{
      await navigator.clipboard.writeText(readableText)
      setCopied(true)
      window.setTimeout(()=>setCopied(false),2000)
    }catch{
      setCopied(false)
    }
  }

  return <section className="card overflow-hidden" aria-labelledby="ocr-heading">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
      <div>
        <h2 id="ocr-heading">Văn bản OCR</h2>
        <p className="mt-1 text-sm text-slate-500">Bản đọc dễ hiểu đã được tự động làm sạch; nội dung có thể vẫn còn sai sót.</p>
      </div>
      <button type="button" className="button-subtle shrink-0" disabled={!readableText} onClick={copyText} aria-live="polite">
        {copied?'Đã sao chép':'Sao chép'}
      </button>
    </div>

    <div className="p-5">
      {readableText
        ?<div className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-slate-50 px-5 py-4 font-sans text-[0.975rem] leading-7 text-slate-800">{readableText}</div>
        :<div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center">
          <p className="font-medium text-slate-700">Chưa có văn bản OCR</p>
          <p className="mt-1 text-sm text-slate-500">Hãy xử lý tài liệu để hệ thống nhận dạng và hiển thị nội dung tại đây.</p>
        </div>}

      {raw&&<details className="mt-5 border-t border-slate-200 pt-4">
        <summary className="cursor-pointer select-none text-sm font-medium text-slate-700 hover:text-slate-950">Văn bản OCR thô (dành cho kỹ thuật)</summary>
        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-900 p-4 text-xs leading-5 text-slate-100">{raw}</pre>
      </details>}
    </div>
  </section>
}
