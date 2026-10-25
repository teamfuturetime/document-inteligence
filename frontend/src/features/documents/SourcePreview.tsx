import { useState } from 'react';
import type { DocumentDetail } from './api';

export function SourcePreview({ document, active }: { document: DocumentDetail; active: string }) {
  const [zoom, setZoom] = useState(1);
  const [imageError, setImageError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const field = (document.run.fields ?? []).find((item) => item.field_id === active);
  const evidence = (document.run.spans ?? []).filter((span) =>
    field?.evidence_span_ids.includes(span.span_id),
  );
  return (
    <section className="source-panel" aria-label="Đối chiếu ảnh nguồn">
      <div className="panel-heading">
        <div>
          <h2>Ảnh nguồn</h2>
          <p className="subtle">Chọn một trường để xem bằng chứng OCR.</p>
        </div>
        <label>
          Thu phóng{' '}
          <select value={zoom} onChange={(event) => setZoom(Number(event.target.value))}>
            <option value={1}>100%</option>
            <option value={1.5}>150%</option>
            <option value={2}>200%</option>
          </select>
        </label>
      </div>
      {imageError && (
        <div role="alert">
          <p>Không tải được ảnh nguồn.</p>
          <button
            onClick={() => {
              setAttempt((old) => old + 1);
              setImageError(false);
            }}
          >
            Thử tải lại ảnh
          </button>
        </div>
      )}
      <div className="source-scroll">
        <div className="source-canvas" style={{ width: `${zoom * 100}%` }}>
          <img
            src={`${document.image_url}?retry=${attempt}`}
            alt={`Ảnh nguồn ${document.filename}`}
            onError={() => setImageError(true)}
          />
          <svg
            viewBox={`0 0 ${document.image_width} ${document.image_height}`}
            role="img"
            aria-label="Bằng chứng OCR của trường đang chọn"
          >
            {evidence.map((span) => (
              <rect
                key={span.span_id}
                x={span.box[0]}
                y={span.box[1]}
                width={span.box[2] - span.box[0]}
                height={span.box[3] - span.box[1]}
              />
            ))}
          </svg>
        </div>
      </div>
      <p className="subtle">
        {evidence.length
          ? `${evidence.length} vùng chữ được dùng làm bằng chứng.`
          : 'Trường này chưa có bằng chứng nguồn; hãy đối chiếu trực tiếp.'}
      </p>
    </section>
  );
}
