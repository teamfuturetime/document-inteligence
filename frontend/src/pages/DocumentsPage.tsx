import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getApiErrorMessage, listDocuments } from "../services/api";
import type { DocumentRecord } from "../types/document";
import { typeLabels } from "../types/labels";

const statusLabel: Record<string, string> = {
  uploaded: "Đã tải", processing: "Đang xử lý", review: "Cần kiểm tra",
  confirmed: "Đã xác nhận", failed: "Có lỗi",
};
const PAGE_SIZE = 10;
const emptyFilters = { query: "", status: "", documentType: "" };

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [draft, setDraft] = useState(emptyFilters);
  const [filters, setFilters] = useState(emptyFilters);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    void listDocuments({ ...filters, offset: page * PAGE_SIZE, limit: PAGE_SIZE, signal: controller.signal })
      .then(data => {
        if (controller.signal.aborted) return;
        setDocuments(data.items);
        setTotal(data.total);
      })
      .catch(err => {
        if (!controller.signal.aborted) {
          setError(getApiErrorMessage(err, "Không tải được lịch sử tài liệu. Vui lòng thử lại."));
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters, page, attempt]);

  function search(event: FormEvent) {
    event.preventDefault();
    setPage(0);
    setFilters({ ...draft, query: draft.query.trim() });
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return <main className="mx-auto max-w-5xl p-6">
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl font-bold">Lịch sử tài liệu</h1>
        {!loading && !error && <p role="status" className="mt-2 text-slate-600">{total} tài liệu phù hợp</p>}
      </div>
      <Link className="rounded bg-brand px-4 py-3 font-bold text-white" to="/upload">+ Tải tài liệu</Link>
    </div>
    <form onSubmit={search} className="my-6 flex flex-wrap gap-3 rounded-xl bg-white p-4">
      <input aria-label="Tìm theo tên hoặc ID" className="min-w-0 flex-1 basis-64 rounded border p-3"
        placeholder="Tìm theo tên hoặc ID tài liệu…" value={draft.query}
        onChange={event => setDraft({ ...draft, query: event.target.value })} />
      <select aria-label="Lọc trạng thái" className="rounded border p-3" value={draft.status}
        onChange={event => setDraft({ ...draft, status: event.target.value })}>
        <option value="">Mọi trạng thái</option>
        {Object.entries(statusLabel).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
      </select>
      <select aria-label="Lọc loại tài liệu" className="rounded border p-3" value={draft.documentType}
        onChange={event => setDraft({ ...draft, documentType: event.target.value })}>
        <option value="">Mọi loại tài liệu</option>
        {Object.entries(typeLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
      </select>
      <button disabled={loading} className="rounded border px-5 py-3 font-bold disabled:opacity-50">Tìm</button>
    </form>
    <section aria-label="Kết quả tìm kiếm" aria-busy={loading}>
      {loading && <p role="status" className="p-8 text-center">Đang tải tài liệu…</p>}
      {error && <div className="rounded-xl border border-red-200 bg-white p-6">
        <p role="alert" className="text-red-700">{error}</p>
        <button onClick={() => setAttempt(value => value + 1)} className="mt-3 rounded border px-4 py-2">Thử lại</button>
      </div>}
      {!loading && !error && <>
        <div className="overflow-x-auto rounded-xl border bg-white">
          <table className="w-full text-left">
            <thead className="bg-slate-100"><tr>
              <th scope="col" className="p-4">Tài liệu</th><th scope="col" className="p-4">Loại</th>
              <th scope="col" className="p-4">Trạng thái</th><th scope="col" className="p-4">Ngày tải</th>
            </tr></thead>
            <tbody>{documents.map(doc => <tr className="border-t" key={doc.id}>
              <td className="p-4"><Link className="font-semibold text-brand underline" to={`/documents/${doc.id}`}>{doc.original_name}</Link></td>
              <td className="p-4">{doc.document_type ? typeLabels[doc.document_type] ?? doc.document_type : "Chưa nhận diện"}</td>
              <td className="p-4">{statusLabel[doc.status]}</td>
              <td className="p-4">{new Intl.DateTimeFormat("vi-VN").format(new Date(doc.created_at))}</td>
            </tr>)}</tbody>
          </table>
          {documents.length === 0 && <p className="p-8 text-center text-slate-500">Chưa có tài liệu phù hợp.</p>}
        </div>
        {total > PAGE_SIZE && <nav aria-label="Phân trang" className="mt-4 flex items-center justify-end gap-3">
          <button disabled={page === 0} onClick={() => setPage(value => value - 1)} className="rounded border bg-white px-4 py-2 disabled:opacity-50">Trang trước</button>
          <span>Trang {page + 1}/{pageCount}</span>
          <button disabled={page + 1 >= pageCount} onClick={() => setPage(value => value + 1)} className="rounded border bg-white px-4 py-2 disabled:opacity-50">Trang sau</button>
        </nav>}
      </>}
    </section>
  </main>;
}
