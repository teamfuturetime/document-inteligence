import {useMemo,useState} from 'react'
import type{OCRBlock,OCRPage}from'../types'

type OCRTextCardProps={cleanedText?:string|null;rawText?:string|null;pages?:OCRPage[]|null}
type ViewMode='readable'|'raw'|'structure'

const blockLabels:Record<OCRBlock['type'],string>={heading:'Tiêu đề',paragraph:'Đoạn văn',key_value:'Trường thông tin',table:'Bảng',list:'Danh sách',unknown:'Khối chưa xác định'}

function Confidence({value,needsReview}:{value:number;needsReview:boolean}){
  const percent=Math.round(value*100)
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${needsReview?'bg-amber-100 text-amber-800':'bg-emerald-100 text-emerald-800'}`} title="Độ tin cậy do OCR engine cung cấp">
    OCR {percent}%{needsReview?' · cần kiểm tra':''}
  </span>
}

function StructuredBlock({block}:{block:OCRBlock}){
  return <article className={`rounded-lg border p-4 ${block.needs_review?'border-amber-300 bg-amber-50/40':'border-slate-200 bg-white'}`}>
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{blockLabels[block.type]}</span>
      <Confidence value={block.confidence} needsReview={block.needs_review}/>
    </div>
    {block.type==='table'&&block.rows?.length
      ?<div className="overflow-x-auto"><table className="w-full border-collapse text-left text-sm"><tbody>{block.rows.map((row,rowIndex)=><tr key={rowIndex}>{row.map((cell,cellIndex)=><td className="border border-slate-200 px-3 py-2 align-top" key={cellIndex}>{cell.text}</td>)}</tr>)}</tbody></table><p className="mt-2 text-xs text-amber-700">Cấu trúc bảng được suy ra từ vị trí; hãy đối chiếu số liệu với bản gốc.</p></div>
      :block.type==='key_value'&&block.key
        ?<dl className="grid gap-1 sm:grid-cols-[minmax(8rem,auto)_1fr]"><dt className="font-medium text-slate-700">{block.key}</dt><dd className="whitespace-pre-wrap break-words text-slate-900">{block.value||'—'}</dd></dl>
        :<div className={`whitespace-pre-wrap break-words leading-7 text-slate-800 ${block.type==='heading'?'font-semibold':''}`}>{block.text}</div>}
  </article>
}

function EmptyState({title='Chưa có văn bản OCR',text}:{title?:string;text:string}){
  return <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center"><p className="font-medium text-slate-700">{title}</p><p className="mt-1 text-sm text-slate-500">{text}</p></div>
}

export default function OCRTextCard({cleanedText,rawText,pages}:OCRTextCardProps){
  const [mode,setMode]=useState<ViewMode>('readable')
  const [copied,setCopied]=useState(false)
  const readableText=cleanedText?.trim()||rawText?.trim()||''
  const raw=rawText?.trim()||''
  const structuredText=useMemo(()=>pages?.flatMap(page=>page.blocks.map(block=>block.text)).join('\n\n')||'',[pages])
  const copyValue=mode==='raw'?raw:mode==='structure'?structuredText:readableText
  const tabs:[ViewMode,string][]=[['readable','Văn bản dễ đọc'],['raw','OCR gốc'],['structure','Cấu trúc tài liệu']]

  async function copyText(){
    if(!copyValue)return
    try{await navigator.clipboard.writeText(copyValue);setCopied(true);window.setTimeout(()=>setCopied(false),2000)}catch{setCopied(false)}
  }

  return <section className="card overflow-hidden" aria-labelledby="ocr-heading">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
      <div><h2 id="ocr-heading">Văn bản OCR</h2><p className="mt-1 text-sm text-slate-500">Bản đọc được chuẩn hóa để dễ theo dõi; luôn đối chiếu thông tin quan trọng với bản gốc.</p></div>
      <button type="button" className="button-subtle shrink-0" disabled={!copyValue} onClick={copyText} aria-live="polite">{copied?'Đã sao chép':'Sao chép'}</button>
    </div>
    <div className="border-b border-slate-200 px-3 pt-2" role="tablist" aria-label="Chế độ xem OCR"><div className="flex gap-1 overflow-x-auto">
      {tabs.map(([value,label])=><button key={value} type="button" role="tab" aria-selected={mode===value} onClick={()=>{setMode(value);setCopied(false)}} className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${mode===value?'border-blue-600 text-blue-700':'border-transparent text-slate-500 hover:text-slate-800'}`}>{label}</button>)}
    </div></div>
    <div className="p-5">
      {mode==='readable'&&(readableText?<div className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-white px-5 py-4 font-sans text-[0.975rem] leading-7 text-slate-800">{readableText}</div>:<EmptyState text="Hãy xử lý tài liệu để hệ thống nhận dạng và hiển thị nội dung tại đây."/>)}
      {mode==='raw'&&(raw?<pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-300 bg-slate-50 p-4 text-sm leading-6 text-slate-800">{raw}</pre>:<EmptyState text="Chưa có đầu ra OCR gốc để kiểm tra."/>)}
      {mode==='structure'&&(pages?.length?<div className="space-y-5">{pages.map(page=><section key={page.page_number} aria-label={`Trang ${page.page_number}`}><div className="mb-2 flex items-center justify-between"><h3 className="font-semibold text-slate-800">Trang {page.page_number}</h3><span className="text-xs text-slate-500">{page.width} × {page.height}px</span></div><div className="space-y-3">{page.blocks.map((block,index)=><StructuredBlock key={`${block.bbox.join('-')}-${index}`} block={block}/>)}</div></section>)}</div>:<EmptyState title="Chưa có dữ liệu cấu trúc" text="Tài liệu này chưa có metadata bố cục từ OCR. Hãy xử lý lại để tạo cấu trúc trang."/>)}
    </div>
  </section>
}
