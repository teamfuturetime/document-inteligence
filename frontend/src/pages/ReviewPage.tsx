import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import DocumentPreview from "../components/DocumentPreview";
import { confirmExtraction, getDocument, getExtraction, updateExtraction } from "../services/api";
import type { DocumentRecord, Extraction } from "../types/document";

export default function ReviewPage() {
  const { id = "" } = useParams();
  const [document, setDocument] = useState<DocumentRecord>();
  const [result, setResult] = useState<Extraction>();
  const [message, setMessage] = useState("");
  useEffect(() => { Promise.all([getDocument(id), getExtraction(id)]).then(([doc, ext]) => { setDocument(doc); setResult(ext); }).catch(() => setMessage("Không tải được kết quả.")); }, [id]);
  if (!document || !result) return <main className="p-8" aria-live="polite">{message || "Đang tải kết quả…"}</main>;
  const fields = result.data.fields ?? {};
  function change(name: string, value: string) {
    setResult(current => current && ({ ...current, data: { ...current.data, fields: { ...fields, [name]: { ...fields[name], value } } } }));
  }
  async function save() { if (result) setResult(await updateExtraction(id, result)); setMessage("Đã lưu thay đổi."); }
  async function confirm() { setResult(await confirmExtraction(id)); setMessage("Đã xác nhận kết quả."); }
  return <main className="mx-auto max-w-7xl p-6"><p className="text-sm font-bold uppercase tracking-widest text-brand">Bước 2/2</p><h1 className="my-2 text-3xl font-bold">Kiểm tra thông tin</h1><p className="mb-6 text-slate-600">So sánh với bản gốc, sửa nếu cần rồi xác nhận.</p><div className="grid gap-6 lg:grid-cols-2"><DocumentPreview id={id} mimeType={document.mime_type} name={document.original_name} /><section className="rounded-2xl bg-white p-6 shadow-sm"><h2 className="text-xl font-bold">Dữ liệu nhận diện</h2>{Object.entries(fields).map(([name, field]) => <label className="mt-4 block" key={name}><span className="text-sm font-semibold">{name.replaceAll("_", " ")}</span><input className="mt-1 w-full rounded border p-3" disabled={result.confirmed} value={String(field.value ?? "")} onChange={e => change(name, e.target.value)} /><small className="text-slate-500">Độ tin cậy: {Math.round(field.confidence * 100)}%</small></label>)}{result.warnings.map(warning => <p className="mt-3 text-amber-700" key={warning}>⚠ {warning}</p>)}<div className="mt-6 flex gap-3"><button disabled={result.confirmed} onClick={save} className="rounded border px-5 py-3 font-bold">Lưu sửa đổi</button><button disabled={result.confirmed} onClick={confirm} className="rounded bg-brand px-5 py-3 font-bold text-white">Xác nhận</button></div><p className="mt-3" aria-live="polite">{message}</p></section></div></main>;
}
