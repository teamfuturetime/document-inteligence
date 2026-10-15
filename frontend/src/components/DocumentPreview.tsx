import { documentContentUrl } from "../services/api";

type Props = { id: string; mimeType: string; name: string };

export default function DocumentPreview({ id, mimeType, name }: Props) {
  const url = documentContentUrl(id);
  return <section aria-label="Xem trước tài liệu" className="min-h-[520px] overflow-hidden rounded-2xl border bg-slate-800 p-3">
    {mimeType === "application/pdf"
      ? <iframe className="h-[70vh] w-full rounded bg-white" src={url} title={`Xem trước ${name}`} />
      : <img className="mx-auto max-h-[70vh] rounded object-contain" src={url} alt={`Bản quét ${name}`} />}
  </section>;
}
