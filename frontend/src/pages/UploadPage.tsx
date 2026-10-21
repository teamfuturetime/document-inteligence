import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getApiErrorMessage, processDocument, uploadDocument } from "../services/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return setError("Hãy chọn một tệp trước khi tiếp tục.");
    setBusy(true); setError("");
    try {
      const document = await uploadDocument(file, setProgress);
      await processDocument(document.id);
      navigate(`/documents/${document.id}`);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể xử lý tệp. Kiểm tra định dạng và thử lại."));
      setBusy(false);
    }
  }

  return <main className="mx-auto max-w-2xl p-6"><p className="text-sm font-bold uppercase tracking-widest text-brand">Bước 1/2</p><h1 className="mt-2 text-3xl font-bold">Tải biểu mẫu lên</h1><p className="mt-2 text-slate-600">Hỗ trợ PDF, JPG, JPEG, PNG; tối đa 15 MB. Bạn luôn được kiểm tra trước khi xác nhận.</p><form onSubmit={submit} className="mt-8 rounded-2xl border-2 border-dashed border-slate-300 bg-white p-8"><label className="block font-semibold" htmlFor="file">Chọn tài liệu</label><input id="file" className="mt-3 block w-full" type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />{file && <p className="mt-4 rounded bg-paper p-3">{file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB</p>}{busy && <progress className="mt-4 w-full" value={progress} max="100" />}{error && <p role="alert" className="mt-4 text-red-700">{error}</p>}<button disabled={busy} className="mt-6 rounded-lg bg-brand px-5 py-3 font-bold text-white disabled:opacity-50">{busy ? "Đang xử lý…" : "Tải lên và nhận diện"}</button></form></main>;
}
