import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import DocumentPreview from "../components/DocumentPreview";
import { confirmExtraction, getApiErrorMessage, getDocument, getExtraction, processDocument, updateExtraction } from "../services/api";
import type { DocumentRecord, Extraction } from "../types/document";
import { fieldLabels, typeLabels } from "../types/labels";

export default function ReviewPage() {
  const { id = "" } = useParams();
  const [document, setDocument] = useState<DocumentRecord>();
  const [result, setResult] = useState<Extraction>();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    let active = true;
    setDocument(undefined); setResult(undefined); setError(""); setMessage(""); setDirty(false);
    void (async () => {
      try {
        const doc = await getDocument(id);
        if (!active) return;
        setDocument(doc);
        if (["review", "confirmed"].includes(doc.status)) {
          const ext = await getExtraction(id);
          if (active) setResult(ext);
        }
      } catch (err) { if (active) setError(getApiErrorMessage(err, "Không tải được tài liệu.")); }
    })();
    return () => { active = false; };
  }, [id]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  async function run(action: "save" | "confirm" | "process") {
    if (busy) return;
    if (action === "process" && dirty && !window.confirm("Xử lý lại sẽ thay thế các sửa đổi chưa lưu. Tiếp tục?")) return;
    setBusy(true); setError(""); setMessage("");
    try {
      if (action === "process") {
        await processDocument(id);
        setResult(await getExtraction(id));
      } else if (result) {
        setResult(await updateExtraction(id, result));
        if (action === "confirm") setResult(await confirmExtraction(id));
      }
      setDirty(false);
      setDocument(await getDocument(id));
      setMessage(action === "confirm" ? "Đã lưu và xác nhận kết quả." : action === "save" ? "Đã lưu sửa đổi." : "Đã nhận diện lại. Hãy đối chiếu với bản gốc.");
    } catch (err) { setError(getApiErrorMessage(err, "Thao tác chưa thành công. Vui lòng thử lại.")); }
    finally { setBusy(false); }
  }
  function change(name: string, value: string) {
    setResult(current => current && ({ ...current, data: { ...current.data, fields: { ...current.data.fields,
      [name]: { ...current.data.fields![name], value, reviewed: true } } } }));
    setDirty(true); setMessage("");
  }
  function download() {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }));
    const link = window.document.createElement("a"); link.href = url; link.download = `${document?.original_name ?? "document"}.json`; link.click();
    URL.revokeObjectURL(url);
  }
  if (!document) return <main className="p-8"><p role={error ? "alert" : "status"}>{error || "Đang tải tài liệu…"}</p><Link to="/documents">Về lịch sử</Link></main>;
  const fields = result?.data.fields ?? {};
  return <main className="mx-auto max-w-7xl p-6">
    <Link to="/documents" className="text-sm text-brand underline">← Lịch sử tài liệu</Link>
    <h1 className="mt-4 text-3xl font-bold">Kiểm tra thông tin</h1>
    <p className="mt-2 break-all text-slate-600">{document.original_name} · {typeLabels[document.document_type ?? "unknown"] ?? document.document_type}</p>
    <p className="mb-6 mt-2 text-sm text-slate-600">Đối chiếu với bản gốc trước khi xác nhận. Chỉ số OCR phản ánh khả năng đọc chữ, không bảo đảm nội dung chính xác.</p>
    <div className="grid items-start gap-6 lg:grid-cols-2">
      <DocumentPreview id={id} mimeType={document.mime_type} name={document.original_name} />
      <section className="rounded-2xl bg-white p-6 shadow-sm" aria-busy={busy}>
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-bold">{result?.confirmed ? "Đã xác nhận" : "Dữ liệu cần kiểm tra"}</h2>
          {result && <button onClick={download} className="rounded border px-3 py-2 text-sm">Xuất JSON{dirty ? " (bản nháp)" : ""}</button>}</div>
        {!result && <p className="my-4">{document.status === "processing" ? "Tài liệu đang xử lý. Tải lại trang sau ít phút." : "Tài liệu chưa có kết quả. Bấm nhận diện để bắt đầu hoặc thử lại."}</p>}
        {Object.entries(fields).sort(([a], [b]) => a.localeCompare(b)).map(([name, field]) => <label className="mt-5 block" key={name}>
          <span className="font-semibold">{fieldLabels[name] ?? name}</span>
          <input className="mt-2 w-full rounded-lg border p-3 disabled:bg-slate-100" disabled={busy || result?.confirmed} value={String(field.value ?? "")} placeholder="Nhập thông tin từ bản gốc" onChange={e => change(name, e.target.value)} />
          <small className={field.confidence < .75 && !field.reviewed ? "text-amber-700" : "text-slate-500"}>{field.reviewed ? "Đã chỉnh sửa thủ công" : field.value ? `Chất lượng đọc OCR: ${Math.round(field.confidence * 100)}% · cần đối chiếu` : "Chưa đọc được — vui lòng bổ sung"}</small>
          {field.source_text && <details className="mt-1 text-xs text-slate-500"><summary className="cursor-pointer">Văn bản nguồn</summary>{field.source_text}</details>}
        </label>)}
        {result?.warnings.filter(w => !w.startsWith("Không tìm thấy trường:")).map(w => <p className="mt-4 text-amber-700" key={w}>{w}</p>)}
        {result?.data.raw_text && <details className="mt-6 rounded-lg border p-3"><summary className="cursor-pointer font-semibold">Xem toàn bộ văn bản OCR</summary><pre className="mt-3 whitespace-pre-wrap text-sm">{result.data.raw_text}</pre></details>}
        <div className="mt-6 flex flex-wrap gap-3">
          {result && !result.confirmed && <><button disabled={busy || !dirty} onClick={() => void run("save")} className="rounded-lg border px-4 py-3 disabled:opacity-50">Lưu sửa đổi</button><button disabled={busy} onClick={() => void run("confirm")} className="rounded-lg bg-brand px-4 py-3 font-bold text-white disabled:opacity-50">Lưu và xác nhận</button></>}
          {!result?.confirmed && <button disabled={busy || document.status === "processing"} onClick={() => void run("process")} className="rounded-lg border px-4 py-3 disabled:opacity-50">{result ? "Nhận diện lại" : "Nhận diện tài liệu"}</button>}
        </div>
        {dirty && <p className="mt-3 text-sm text-amber-700">Có sửa đổi chưa lưu.</p>}
        <p className="mt-3" role="status">{busy ? "Đang xử lý, vui lòng chờ…" : message}</p>
        {error && <p role="alert" className="mt-3 text-red-700">{error}</p>}
      </section>
    </div>
  </main>;
}
