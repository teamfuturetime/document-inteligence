import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDocuments } from "../services/api";
import type { DocumentRecord } from "../types/document";

const statusLabel: Record<string, string> = { uploaded: "Đã tải", processing: "Đang xử lý", review: "Cần kiểm tra", confirmed: "Đã xác nhận", failed: "Có lỗi" };

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [total, setTotal] = useState(0);
  async function load() { const data = await listDocuments(query, status); setDocuments(data.items); setTotal(data.total); }
  useEffect(() => { void load(); }, []);
  function search(event: FormEvent) { event.preventDefault(); void load(); }
  return <main className="mx-auto max-w-5xl p-6"><div className="flex items-end justify-between"><div><h1 className="text-3xl font-bold">Lịch sử tài liệu</h1><p className="mt-2 text-slate-600">{total} tài liệu trong hệ thống</p></div><Link className="rounded bg-brand px-4 py-3 font-bold text-white" to="/upload">+ Tải tài liệu</Link></div><form onSubmit={search} className="my-6 flex flex-wrap gap-3 rounded-xl bg-white p-4"><input aria-label="Tìm theo tên" className="min-w-64 flex-1 rounded border p-3" placeholder="Tìm theo tên tài liệu…" value={query} onChange={e => setQuery(e.target.value)} /><select aria-label="Lọc trạng thái" className="rounded border p-3" value={status} onChange={e => setStatus(e.target.value)}><option value="">Mọi trạng thái</option>{Object.entries(statusLabel).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select><button className="rounded border px-5 font-bold">Tìm</button></form><div className="overflow-x-auto rounded-xl border bg-white"><table className="w-full text-left"><thead className="bg-slate-100"><tr><th className="p-4">Tài liệu</th><th className="p-4">Loại</th><th className="p-4">Trạng thái</th><th className="p-4">Ngày tải</th></tr></thead><tbody>{documents.map(doc => <tr className="border-t" key={doc.id}><td className="p-4"><Link className="font-semibold text-brand underline" to={`/documents/${doc.id}`}>{doc.original_name}</Link></td><td className="p-4">{doc.document_type ?? "Chưa xác định"}</td><td className="p-4">{statusLabel[doc.status]}</td><td className="p-4">{new Intl.DateTimeFormat("vi-VN").format(new Date(doc.created_at))}</td></tr>)}</tbody></table>{documents.length === 0 && <p className="p-8 text-center text-slate-500">Chưa có tài liệu phù hợp.</p>}</div></main>;
}
