import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {Check,Copy,Pencil,Save,X} from 'lucide-react'
import type{OCRBlock,OCRPage}from'../types'
import {ApiError} from '../api/client'
import {OCR_DRAFT_PREFIX} from '../utils/ocrDrafts'

type OCRSaveResult={ocr_revision:number;ocr_text_cleaned?:string|null}
type Props={documentKey?:string;cleanedText?:string|null;rawText?:string|null;pages?:OCRPage[]|null;corrected?:boolean;readOnly?:boolean;revision?:number;onSave?:(text:string,expectedRevision:number)=>Promise<OCRSaveResult>;onDirtyChange?:(dirty:boolean)=>void}
type StoredDraft={text:string;expected_revision:number}
function readDraft(key?:string):StoredDraft|undefined{
 if(!key)return
 try{const value=JSON.parse(sessionStorage.getItem(key)||'null');if(value&&typeof value.text==='string'&&value.text.length<=1000000&&Number.isInteger(value.expected_revision)&&value.expected_revision>=0)return value}catch{/* Storage may be unavailable in private browser contexts. */}
}
type ViewMode='readable'|'raw'|'structure'
const blockLabels:Record<OCRBlock['type'],string>={heading:'Tiêu đề',paragraph:'Đoạn văn',key_value:'Trường thông tin',table:'Bảng',list:'Danh sách',unknown:'Khối chưa xác định'}

function Confidence({value,needsReview}:{value:number;needsReview:boolean}){const percent=Math.round(value*100);return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${needsReview?'bg-amber-100 text-amber-800':'bg-emerald-100 text-emerald-800'}`} title="Độ tin cậy do OCR engine cung cấp">OCR {percent}%{needsReview?' · cần kiểm tra':''}</span>}
function StructuredBlock({block}:{block:OCRBlock}){return <article className={`rounded-lg border p-4 ${block.needs_review?'border-amber-300 bg-amber-50/40':'border-slate-200 bg-white'}`}><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{blockLabels[block.type]}</span><Confidence value={block.confidence} needsReview={block.needs_review}/></div>{block.type==='table'&&block.rows?.length?<div className="overflow-x-auto"><table className="w-full border-collapse text-left text-sm"><tbody>{block.rows.map((row,i)=><tr key={i}>{row.map((cell,j)=><td className="border border-slate-200 px-3 py-2 align-top" key={j}>{cell.text}</td>)}</tr>)}</tbody></table><p className="mt-2 text-xs text-amber-700">Cấu trúc bảng được suy ra từ vị trí; hãy đối chiếu số liệu với bản gốc.</p></div>:block.type==='key_value'&&block.key?<dl className="grid gap-1 sm:grid-cols-[minmax(8rem,auto)_1fr]"><dt className="font-medium text-slate-700">{block.key}</dt><dd className="whitespace-pre-wrap break-words text-slate-900">{block.value||'—'}</dd></dl>:<div className={`whitespace-pre-wrap break-words leading-7 text-slate-800 ${block.type==='heading'?'font-semibold':''}`}>{block.text}</div>}</article>}
function EmptyState({title='Chưa có văn bản OCR',text}:{title?:string;text:string}){return <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center"><p className="font-medium text-slate-700">{title}</p><p className="mt-1 text-sm text-slate-500">{text}</p></div>}

export default function OCRTextCard({documentKey,cleanedText,rawText,pages,corrected=false,readOnly=false,revision=0,onSave,onDirtyChange}:Props){
 const storageKey=documentKey?`${OCR_DRAFT_PREFIX}${documentKey}`:undefined
 const[recovery]=useState(()=>readDraft(storageKey));const[unacknowledged,setUnacknowledged]=useState(Boolean(recovery))
 const[notice,setNotice]=useState(recovery?'Đã khôi phục bản nháp trong tab này. Nội dung chưa được xác nhận lưu; hãy kiểm tra trước khi tiếp tục.':'')
 const[mode,setMode]=useState<ViewMode>('readable');const[copied,setCopied]=useState(false);const[editing,setEditing]=useState(Boolean(recovery));const[draft,setDraft]=useState(recovery?.text||'');const[saving,setSaving]=useState(false);const[message,setMessage]=useState('');const[error,setError]=useState('')
 const readableText=cleanedText?.trim()?cleanedText:rawText?.trim()?rawText:'';const raw=rawText||''
 const[savedText,setSavedText]=useState(readableText)
 const mounted=useRef(false);const inFlight=useRef(false);const currentRevision=useRef(recovery?.expected_revision??revision);const draftRef=useRef(draft)
 const saveHandler=useRef(onSave);const copyTimer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined)
 const dirty=editing&&(draft!==savedText||saving||unacknowledged)
 const status=saving?'Đang lưu…':dirty?'Chưa lưu. Tự động lưu sau khi ngừng nhập.':message
 useEffect(()=>{saveHandler.current=onSave},[onSave])
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;if(copyTimer.current)clearTimeout(copyTimer.current)}},[])
 // Never silently rebase a draft onto another client's revision while editing.
 useEffect(()=>{if(!editing&&revision>currentRevision.current&&!inFlight.current){currentRevision.current=revision;setSavedText(readableText)}},[revision,readableText,editing])
 const copyingDraft=editing&&mode==='readable'
 const structuredText=useMemo(()=>pages?.flatMap(p=>p.blocks.map(b=>b.text)).join('\n\n')||'',[pages]);const copyValue=copyingDraft?draft:mode==='raw'?raw:mode==='structure'?structuredText:readableText
 const tabs:[ViewMode,string][]=[['readable','Văn bản dễ đọc'],['raw','OCR gốc'],['structure','Cấu trúc tài liệu']]
 useEffect(()=>{onDirtyChange?.(dirty);return()=>onDirtyChange?.(false)},[dirty,onDirtyChange])
 useEffect(()=>{const warn=(event:BeforeUnloadEvent)=>{if(dirty){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[dirty])
 const persistDraft=useCallback((text:string,expected_revision:number)=>{
  if(!storageKey)return
  try{sessionStorage.setItem(storageKey,JSON.stringify({text,expected_revision}))}
  catch{setNotice('Trình duyệt không thể giữ bản nháp khi rời trang. Hãy sao chép nội dung trước khi điều hướng.')}
 },[storageKey])
 function forgetDraft(){if(storageKey){try{sessionStorage.removeItem(storageKey)}catch{/* Keep the visible draft if browser storage is unavailable. */}}setUnacknowledged(false);setNotice('')}
 function changeDraft(text:string){draftRef.current=text;setDraft(text);if(text===savedText&&!inFlight.current&&!unacknowledged)forgetDraft();else persistDraft(text,currentRevision.current);setMessage('');if(!error.startsWith('Xung đột'))setError('')}
 function changeMode(next:ViewMode){if(inFlight.current)return;if(dirty&&!window.confirm('Bạn có thay đổi OCR chưa lưu. Bạn có muốn bỏ các thay đổi này?'))return;if(dirty){setEditing(false);setDraft('');draftRef.current='';forgetDraft()}setMode(next);setCopied(false);setError('');setMessage('')}
 function startEdit(){setMode('readable');setSavedText(readableText);setDraft(readableText);draftRef.current=readableText;setEditing(true);setError('');setMessage('')}
 function cancel(){if(dirty&&!window.confirm('Bỏ các thay đổi OCR chưa lưu?'))return;setEditing(false);setDraft('');draftRef.current='';forgetDraft();setError('')}
 const save=useCallback(async()=>{
  // Serialize requests while leaving typing enabled; each acknowledgement applies
  // only to its captured text, then the newest draft gets a fresh debounce.
  if(inFlight.current||readOnly||!editing||!saveHandler.current)return
  if(!draft.trim()){setError('Văn bản OCR không được để trống.');return}
  const snapshot=draft;const expected=currentRevision.current
  inFlight.current=true;setSaving(true);setError('');setMessage('')
  try{
   const result=await saveHandler.current(snapshot,expected)
   if(!mounted.current)return
   if(!result||result.ocr_revision<=expected||result.ocr_text_cleaned!==snapshot)throw new Error('Máy chủ chưa xác nhận nội dung OCR. Bản nháp được giữ lại.')
   currentRevision.current=result.ocr_revision;setSavedText(snapshot);setUnacknowledged(false);setNotice('');setMessage('Đã lưu văn bản OCR chỉnh sửa.')
   if(draftRef.current===snapshot){if(storageKey){try{sessionStorage.removeItem(storageKey)}catch{/* A future recovery will require server confirmation again. */}}}
   else persistDraft(draftRef.current,result.ocr_revision)
  }catch(e){
   if(!mounted.current)return
   setUnacknowledged(true);setError(e instanceof ApiError&&e.status===409?'Xung đột phiên bản hoặc trạng thái tài liệu đã thay đổi. Bản nháp vẫn được giữ; hãy sao chép nội dung trước khi tải lại.':e instanceof Error?e.message:'Không thể lưu văn bản OCR.')
  }finally{inFlight.current=false;if(mounted.current)setSaving(false)}
 },[draft,readOnly,editing,storageKey,persistDraft])
 useEffect(()=>{
  if(!editing||readOnly||saving||!dirty||error)return
  const timer=setTimeout(()=>{void save()},800)
  return()=>clearTimeout(timer)
 },[editing,readOnly,saving,dirty,error,save])
 async function copyText(){if(!copyValue)return;try{await navigator.clipboard.writeText(copyValue);if(!mounted.current)return;setCopied(true);copyTimer.current=setTimeout(()=>setCopied(false),2000)}catch{if(mounted.current)setError('Không thể sao chép văn bản.')}}
 return <section className="card overflow-hidden" aria-labelledby="ocr-heading"><div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-5 py-4"><div><div className="flex flex-wrap items-center gap-2"><h2 id="ocr-heading">Văn bản OCR</h2>{corrected&&<span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-800"><Check size={13}/>Đã được người dùng chỉnh sửa</span>}</div><p className="mt-1 text-sm text-slate-500">Bản dễ đọc có thể được hiệu chỉnh; OCR gốc luôn được giữ nguyên để đối chiếu.</p></div><div className="flex flex-wrap gap-2">{!editing&&!readOnly&&onSave&&<button type="button" className="button-primary" onClick={startEdit}><Pencil size={16}/>Chỉnh sửa văn bản OCR</button>}<button type="button" className="button-subtle shrink-0" disabled={!copyValue} onClick={copyText}><Copy size={16}/>{copied?'Đã sao chép':copyingDraft?'Sao chép bản nháp':'Sao chép'}</button></div></div>{readOnly&&<div className="border-b border-emerald-200 bg-emerald-50 px-5 py-3 text-sm text-emerald-800">Văn bản OCR hiện ở chế độ chỉ đọc.</div>}{notice&&<div role="note" className="border-b border-amber-200 bg-amber-50 px-5 py-3 text-sm text-amber-800">{notice}</div>}{status&&<div role="status" className="border-b border-emerald-200 bg-emerald-50 px-5 py-3 text-sm text-emerald-800">{status}</div>}{error&&<div role="alert" className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm text-red-700">{error}</div>}<div className="border-b border-slate-200 px-3 pt-2" role="tablist" aria-label="Chế độ xem OCR"><div className="flex gap-1 overflow-x-auto">{tabs.map(([value,label])=><button key={value} type="button" role="tab" aria-selected={mode===value} onClick={()=>changeMode(value)} className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${mode===value?'border-blue-600 text-blue-700':'border-transparent text-slate-500 hover:text-slate-800'}`}>{label}</button>)}</div></div><div className="p-5">{mode==='readable'&&(editing?<div><label className="block font-medium text-slate-700" htmlFor="ocr-editor">Nội dung OCR đã hiệu chỉnh</label><textarea id="ocr-editor" aria-label="Nội dung OCR đã hiệu chỉnh" className="mt-2 min-h-80 w-full whitespace-pre-wrap font-sans leading-7" value={draft} disabled={readOnly} maxLength={1000000} onChange={e=>changeDraft(e.target.value)}/><div className="mt-3 flex flex-wrap gap-2"><button type="button" className="button-primary" disabled={readOnly||saving||!dirty} onClick={save}><Save size={16}/>{saving?'Đang lưu…':'Lưu OCR'}</button><button type="button" className="button-subtle" disabled={saving} onClick={cancel}><X size={16}/>Hủy</button></div></div>:readableText?<div className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-white px-5 py-4 font-sans text-[0.975rem] leading-7 text-slate-800">{readableText}</div>:<EmptyState text="Hãy xử lý tài liệu để hệ thống nhận dạng và hiển thị nội dung tại đây."/>)}{mode==='raw'&&(raw?<pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-300 bg-slate-50 p-4 text-sm leading-6 text-slate-800">{raw}</pre>:<EmptyState text="Chưa có đầu ra OCR gốc để kiểm tra."/>)}{mode==='structure'&&(pages?.length?<div className="space-y-5">{pages.map(page=><section key={page.page_number} aria-label={`Trang ${page.page_number}`}><div className="mb-2 flex items-center justify-between"><h3 className="font-semibold text-slate-800">Trang {page.page_number}</h3><span className="text-xs text-slate-500">{page.width} × {page.height}px</span></div><div className="space-y-3">{page.blocks.map((block,index)=><StructuredBlock key={`${block.bbox.join('-')}-${index}`} block={block}/>)}</div></section>)}</div>:<EmptyState title="Chưa có dữ liệu cấu trúc" text="Tài liệu này chưa có metadata bố cục từ OCR. Hãy xử lý lại để tạo cấu trúc trang."/>)}</div></section>
}
