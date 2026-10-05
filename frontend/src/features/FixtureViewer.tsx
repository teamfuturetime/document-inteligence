import { useEffect, useState } from 'react';
import { Notice } from '../components/Notice';
import { getJson } from '../lib/api';
import type { FieldId, FixtureCatalog, FixtureView } from '../lib/api';

const labels: Record<FieldId, string> = {
  full_name: 'Họ và tên',
  student_id: 'Mã sinh viên',
  date_of_birth: 'Ngày sinh',
  class_name: 'Lớp',
  faculty: 'Khoa',
  request_content: 'Nội dung đề nghị',
  request_date: 'Ngày làm đơn',
};

export function FixtureViewer({ mode }: { mode: 'fixture' | 'unconfigured' }) {
  const [catalog, setCatalog] = useState<string[]>([]);
  const [sample, setSample] = useState('');
  const [view, setView] = useState<FixtureView | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [active, setActive] = useState<FieldId>('full_name');
  useEffect(() => {
    if (mode !== 'fixture') return;
    const controller = new AbortController();
    setError('');
    getJson<FixtureCatalog>('/fixtures', controller.signal)
      .then((result) => {
        setCatalog(result.sample_ids);
        setSample((old) => (result.sample_ids.includes(old) ? old : (result.sample_ids[0] ?? '')));
      })
      .catch((reason: Error) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, [mode, attempt]);
  useEffect(() => {
    if (!sample) return;
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setView(null);
    getJson<FixtureView>(`/fixtures/${encodeURIComponent(sample)}`, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setView(result);
      })
      .catch((reason: Error) => {
        if (!controller.signal.aborted) setError(reason.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [sample, attempt]);
  if (mode !== 'fixture')
    return (
      <Notice message="Chế độ fixture chưa bật. Cấu hình DOCINTEL_PROVIDER_MODE=fixture để xem mẫu. OCR thật chưa triển khai." />
    );
  const activePrediction = view?.run.fields.find((field) => field.field_id === active);
  const spans =
    view?.run.spans.filter((span) => activePrediction?.evidence_span_ids?.includes(span.span_id)) ??
    [];
  return (
    <>
      <div className="fixture-banner">
        <strong>Mẫu giả lập — chưa chạy OCR</strong>
        <p>
          Ảnh và dự đoán synthetic phục vụ kiểm tra contract. Một số dự đoán sai có chủ ý. Không
          dùng làm bằng chứng chất lượng AI.
        </p>
      </div>
      {error && <Notice message={error} retry={() => setAttempt(attempt + 1)} />}
      <div className="sample-toolbar">
        <label htmlFor="sample">Chọn mẫu</label>
        <select id="sample" value={sample} onChange={(event) => setSample(event.target.value)}>
          {catalog.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        <span className="subtle">Bấm vào trường để xem bằng chứng giả lập.</span>
      </div>
      {loading && <p role="status">Đang tải mẫu minh họa…</p>}
      {!loading && !error && !catalog.length && <p role="status">Chưa có mẫu minh họa.</p>}
      {view && (
        <div className="review-grid">
          <article className="source-panel">
            <div className="panel-heading">
              <h2>Ảnh nguồn</h2>
              <span className="pill soft">SYNTHETIC</span>
            </div>
            <div className="image-stage">
              <img src={view.image_url} alt={`Đơn đề nghị giả lập ${sample}; thông tin hư cấu`} />
              <svg
                viewBox="0 0 1100 1400"
                aria-label="Vùng bằng chứng của trường đang chọn"
                role="img"
              >
                {spans.map(
                  (span) =>
                    span.polygon && (
                      <polygon
                        key={span.span_id}
                        points={span.polygon.map((point) => `${point.x},${point.y}`).join(' ')}
                      />
                    ),
                )}
              </svg>
            </div>
            <p className="subtle">Trang 1 · tọa độ pixel ảnh gốc · bằng chứng từ fixture</p>
          </article>
          <article className="fields-panel">
            <div className="panel-heading">
              <h2>Dự đoán máy giả lập</h2>
              <span className="pill soft">CHỈ XEM</span>
            </div>
            <p className="subtle">
              Confidence: chưa đo, không phải xác suất đúng. Validation đạt vẫn cần đối chiếu nguồn.
            </p>
            <div className="field-list">
              {view.run.fields.map((field) => {
                const issues = view.validation_issues.filter(
                  (issue) => issue.field_path === field.field_id,
                );
                return (
                  <div
                    key={field.field_id}
                    className={`field-row ${active === field.field_id ? 'active' : ''}`}
                  >
                    <label htmlFor={field.field_id}>{labels[field.field_id]}</label>
                    <div className="field-value">
                      {field.field_id === 'request_content' ? (
                        <textarea
                          id={field.field_id}
                          readOnly
                          value={field.normalized_value ?? ''}
                          onFocus={() => setActive(field.field_id)}
                          aria-describedby={`${field.field_id}-status`}
                        />
                      ) : (
                        <input
                          id={field.field_id}
                          readOnly
                          value={field.normalized_value ?? ''}
                          onFocus={() => setActive(field.field_id)}
                          aria-describedby={`${field.field_id}-status`}
                        />
                      )}
                      <button
                        className="evidence-button"
                        aria-label={`Xem bằng chứng: ${labels[field.field_id]}`}
                        onClick={() => setActive(field.field_id)}
                      >
                        ↗
                      </button>
                    </div>
                    <small id={`${field.field_id}-status`}>
                      {field.observation === 'found'
                        ? 'Có giá trị'
                        : field.observation === 'unreadable'
                          ? 'Không đọc được'
                          : 'Chưa tìm thấy'}{' '}
                      ·{' '}
                      {field.evidence_status === 'available'
                        ? 'Có bằng chứng giả lập'
                        : 'Không có bằng chứng'}{' '}
                      · Chưa review
                    </small>
                    {issues.map((issue) => (
                      <p className="field-error" key={issue.code}>
                        {issue.message}
                      </p>
                    ))}
                  </div>
                );
              })}
            </div>
            <div className="demo-actions">
              <button disabled>Lưu nháp</button>
              <button disabled>Xác nhận</button>
              <button disabled>Xuất JSON</button>
              <p>
                Chưa triển khai sửa/lưu, xác nhận và export. JSON mẫu chỉ là ví dụ contract trong
                repository.
              </p>
            </div>
          </article>
        </div>
      )}
    </>
  );
}
