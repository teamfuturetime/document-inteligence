import{useCallback,useEffect,useMemo,useRef,useState}from'react'
import{CheckCircle,Plus,Pencil,RotateCcw,Save,Trash2,X}from'lucide-react'
import{Link,useBlocker,useParams}from'react-router-dom'
import{ApiError,api}from'../api/client'
import OCRTextCard from'../components/OCRTextCard'
import DocumentPreview from'../components/DocumentPreview'
import StatusBadge from'../components/StatusBadge'
import type{Document,Extraction}from'../types'
import{emptyExtractionMessage,extractedFieldLabel,extractionNotice}from'../utils/extractedFields'

type FieldRow={id:string;key:string;value:string;original?:unknown}
const documentTypes=[['unknown','Chưa xác định'],['cccd','Căn cước công dân'],['cmnd','Chứng minh nhân dân'],['hop_dong_lao_dong','Hợp đồng lao động'],['don_xin_viec','Đơn xin việc'],['ho_khau','Sổ hộ khẩu'],['hoa_don','Hóa đơn'],['invoice','Hóa đơn (mã tương thích)'],['application_form','Biểu mẫu'],['other','Khác']] as const
const typeLabel=(value:string)=>documentTypes.find(([key])=>key===value)?.[1]||value
const displayValue=(value:unknown)=>typeof value==='object'?JSON.stringify(value):String(value??'')
const fieldRows=(data:Record<string,unknown>):FieldRow[]=>Object.entries(data).map(([key,value],index)=>({id:`saved-${index}-${key}`,key,value:displayValue(value),original:value}))

export default function DocumentDetailPage(){
 const{id=''}=useParams()
 return <DocumentReview key={id} id={id}/>
}

function DocumentReview({id}:{id:string}){
 const[doc,setDoc]=useState<Document>();const[ext,setExt]=useState<Extraction>();const[rows,setRows]=useState<FieldRow[]>([]);const[type,setType]=useState('unknown');const[editing,setEditing]=useState(false);const[ocrDirty,setOcrDirty]=useState(false);const[error,setError]=useState('');const[success,setSuccess]=useState('');const[busy,setBusy]=useState(false);const nextId=useMemo(()=>({value:0}),[])
 const mounted=useRef(false);const loadVersion=useRef(0)
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;loadVersion.current++}},[])
 const extractionDirty=editing&&(type!==(ext?.document_type||'unknown')||JSON.stringify(rows.map(r=>[r.key,r.value]))!==JSON.stringify(fieldRows(ext?.data||{}).map(r=>[r.key,r.value])))
 const hasUnsaved=ocrDirty||extractionDirty
 const blocker=useBlocker(({currentLocation,nextLocation})=>hasUnsaved&&(currentLocation.pathname!==nextLocation.pathname||currentLocation.search!==nextLocation.search))
 useEffect(()=>{
  if(blocker.state!=='blocked')return
  if(window.confirm('Bạn có thay đổi chưa lưu. Bạn vẫn muốn rời trang?'))blocker.proceed()
  else blocker.reset()
 },[blocker])
 const resetDraft=useCallback((value?:Extraction)=>{setRows(fieldRows(value?.data||{}));setType(value?.document_type||'unknown')},[])
 const load=useCallback(async()=>{
  const version=++loadVersion.current
  const active=()=>mounted.current&&version===loadVersion.current
  try{
   const d=await api.get(id)
   if(!active())return
   setDoc(current=>!current||d.ocr_revision>=current.ocr_revision?d:current)
   try{const x=await api.extraction(id);if(active()){setExt(x);resetDraft(x)}}
   catch(e){if(!active())return;if(e instanceof ApiError&&e.status===404){setExt(undefined);resetDraft()}else throw e}
  }catch(e){if(active())setError(e instanceof Error?e.message:'Không thể tải tài liệu')}
 },[id,resetDraft])
 useEffect(()=>{void load()},[load])
 useEffect(()=>{const warn=(event:BeforeUnloadEvent)=>{if(hasUnsaved){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[hasUnsaved])
 async function action(fn:()=>Promise<unknown>,message?:string){setBusy(true);setError('');setSuccess('');try{await fn();await load();setEditing(false);if(message)setSuccess(message)}catch(e){setError(e instanceof Error?e.message:'Thao tác thất bại')}finally{setBusy(false)}}
 function startEditing(){resetDraft(ext);setEditing(true);setError('');setSuccess('')}
 function cancelEditing(){if(extractionDirty&&!window.confirm('Bỏ các thay đổi dữ liệu chưa lưu?'))return;resetDraft(ext);setEditing(false);setError('')}
 function addField(){setRows(current=>[...current,{id:`new-${nextId.value++}`,key:'',value:''}])}
 function updateField(index:number,part:'key'|'value',value:string){setRows(current=>current.map((row,i)=>i===index?{...row,[part]:value}:row))}
 async function saveReview(){const names=rows.map(row=>row.key.normalize('NFC').trim());if(names.some(name=>!name)){setError('Tên trường không được để trống.');return}const identities=names.map(name=>name.toLocaleLowerCase('vi'));if(new Set(identities).size!==identities.length){setError('Tên trường không được trùng nhau.');return}const data=Object.fromEntries(rows.map((row,index)=>[names[index],row.original!==undefined&&displayValue(row.original)===row.value?row.original:row.value]));await action(()=>api.save(id,data,type),'Đã lưu dữ liệu rà soát.')}
 async function confirmReview(){if(hasUnsaved||editing){setError('Hãy lưu hoặc hủy mọi thay đổi trước khi xác nhận.');return}await action(()=>api.confirm(id),'Đã xác nhận kết quả. Phiên rà soát chuyển sang chỉ đọc.')}
 if(error&&!doc)return <div className="error">{error} <Link to="/documents">Quay lại</Link></div>;if(!doc)return <p>Đang tải tài liệu…</p>
 const confirmed=doc.status==='confirmed';const reviewable=['processed','reviewed'].includes(doc.status);const showReview=Boolean(ext)||reviewable
 return <><div className="page-title"><div><h1 className="break-all">{doc.filename}</h1><div className="mt-2 flex flex-wrap gap-2"><StatusBadge status={doc.status}/><span className="text-sm text-slate-500">{(doc.file_size/1024).toFixed(0)} KB</span>{confirmed&&<span className="text-sm font-medium text-emerald-700">Chỉ đọc sau xác nhận</span>}</div></div><div className="flex flex-wrap gap-2">{ext&&<a className="button-subtle" href={api.export(id)}>Xuất JSON</a>}{confirmed&&<button disabled={busy} className="button-subtle" onClick={()=>action(()=>api.reopen(id),'Đã mở lại phiên rà soát.')}><RotateCcw size={16}/>Mở lại rà soát</button>}<Link className="button-subtle" to="/documents">Quay lại</Link></div></div>{error&&<div role="alert" className="error mb-4">{error}</div>}{success&&<div role="status" className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{success}</div>}{confirmed&&<div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-900"><b>Kết quả đã được xác nhận.</b> Nội dung hiện ở chế độ chỉ đọc. Chọn “Mở lại rà soát” nếu cần hiệu chỉnh thêm.</div>}<div className="grid gap-6 xl:grid-cols-2"><section className="card overflow-hidden"><div className="border-b p-4 font-semibold">Bản gốc</div><DocumentPreview key={id} document={doc}/></section><section className="space-y-5"><div className="card p-5"><div className="flex flex-wrap items-center justify-between gap-3"><h2>Kết quả nhận dạng</h2>{showReview&&!confirmed&&!editing&&<button className="button-primary" onClick={startEditing}><Pencil size={16}/>Chỉnh sửa dữ liệu</button>}</div>{!showReview?<div className="mt-4"><p className="text-slate-500">Chưa có kết quả trích xuất.</p><button disabled={busy||doc.status==='processing'} className="button-primary mt-4" onClick={()=>action(()=>api.process(id))}>{busy?'Đang xử lý…':'Xử lý bằng AI'}</button></div>:<div className="mt-4"><label className="block">Loại tài liệu{editing?<select aria-label="Loại tài liệu" value={type} onChange={e=>setType(e.target.value)}>{documentTypes.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>:<div className="mt-1 rounded-lg bg-slate-50 px-3 py-2 font-medium">{typeLabel(ext?.document_type||type)}</div>}</label>{ext&&<div className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><div>AI phân loại: <b>{typeLabel(ext.ai_document_type||ext.document_type)}</b></div><div>Người dùng duyệt: <b>{ext.reviewed_document_type?typeLabel(ext.reviewed_document_type):'Chưa duyệt'}</b></div><div className="sm:col-span-2">Độ tin cậy heuristic: <b>{(ext.confidence*100).toFixed(0)}%</b><p className="text-slate-500">Điểm theo luật nhận dạng, không phải xác suất đã hiệu chuẩn.</p></div></div>}</div>}</div>{showReview&&<div className="card p-5"><div className="flex flex-wrap items-center justify-between gap-3"><h2>Trường trích xuất</h2>{editing&&<button type="button" className="button-subtle" onClick={addField}><Plus size={16}/>Thêm trường</button>}</div><p className="mt-3 text-sm text-slate-500">{extractionNotice(ext?.status,ext?.classification_metadata?.source)}</p><div className="mt-4 space-y-3">{rows.length===0?<p className="text-slate-500">{emptyExtractionMessage}</p>:rows.map((row,index)=>editing?<div className="grid gap-2 rounded-lg border border-slate-200 p-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto]" key={row.id}><label>Tên trường<input aria-label={`Tên trường ${index+1}`} maxLength={100} value={row.key} onChange={e=>updateField(index,'key',e.target.value)}/></label><label>Giá trị<input aria-label={`Giá trị trường ${index+1}`} maxLength={10000} value={row.value} onChange={e=>updateField(index,'value',e.target.value)}/></label><button type="button" aria-label={`Xóa trường ${index+1}`} className="self-end rounded-lg p-2 text-red-600 hover:bg-red-50" onClick={()=>setRows(current=>current.filter((_,i)=>i!==index))}><Trash2 size={18}/></button></div>:<dl className="grid gap-1 sm:gap-x-4 rounded-lg border border-slate-100 p-3 sm:grid-cols-[minmax(8rem,auto)_1fr]" key={row.id}><dt className="font-medium text-slate-700">{extractedFieldLabel(row.key)}</dt><dd className="whitespace-pre-wrap break-words">{row.value||'—'}</dd></dl>)}</div><div className="mt-5 flex flex-wrap gap-2">{editing?<><button disabled={busy||!extractionDirty} className="button-primary" onClick={saveReview}><Save size={16}/>{busy?'Đang lưu…':'Lưu thay đổi'}</button><button disabled={busy} className="button-subtle" onClick={cancelEditing}><X size={16}/>Hủy</button></>:!confirmed&&<button disabled={busy||ocrDirty} className="button-success inline-flex items-center gap-2" onClick={confirmReview}><CheckCircle size={16}/>Xác nhận kết quả</button>}</div>{ocrDirty&&<p className="mt-3 text-sm text-amber-700">Hãy lưu hoặc hủy thay đổi OCR trước khi xác nhận.</p>}</div>}<OCRTextCard documentKey={id} revision={doc.ocr_revision} cleanedText={doc.ocr_text_cleaned} rawText={doc.ocr_text_raw??doc.ocr_text} pages={doc.ocr_pages} corrected={doc.ocr_is_corrected} readOnly={!reviewable||busy} onDirtyChange={setOcrDirty} onSave={reviewable?async (text,expectedRevision)=>{const updated=await api.saveOcr(id,text,expectedRevision);if(mounted.current)setDoc(current=>!current||updated.ocr_revision>current.ocr_revision?updated:current);return updated}:undefined}/></section></div></>
}
