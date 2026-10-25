import { useCallback, useEffect, useRef, useState } from 'react';
import type { Capabilities } from '../../lib/api';
import { HistoryPanel } from './HistoryPanel';
import { ReviewPanel } from './ReviewPanel';
import { SourcePreview } from './SourcePreview';
import { jsonRequest, request, statusLabels } from './api';
import type { DocumentDetail, DocumentList, ProductInsights, ProductSchema } from './api';

export function Workspace({
  capabilities,
  onUnsavedChange,
}: {
  capabilities: Capabilities | null;
  onUnsavedChange: (value: boolean) => void;
}) {
  const [schemas, setSchemas] = useState<ProductSchema[]>([]);
  const [list, setList] = useState<DocumentList | null>(null);
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [insights, setInsights] = useState<ProductInsights | null>(null);
  const [type, setType] = useState('hoa_don');
  const [origin, setOrigin] = useState('synthetic');
  const [acknowledged, setAcknowledged] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [active, setActive] = useState('invoice_number');
  const [filter, setFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');
  const uploadKey = useRef<{ signature: string; key: string } | null>(null);
  const onDirtyChange = useCallback(
    (value: boolean) => {
      setDirty(value);
      onUnsavedChange(value);
    },
    [onUnsavedChange],
  );
  useEffect(() => {
    const controller = new AbortController();
    request<ProductSchema[]>('/document-schemas', { signal: controller.signal })
      .then(setSchemas)
      .catch((reason: Error) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ limit: '10', offset: String(offset) });
    if (filter) query.set('status', filter);
    request<DocumentList>(`/documents?${query}`, { signal: controller.signal })
      .then(setList)
      .catch((reason: Error) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    request<ProductInsights>('/insights', { signal: controller.signal })
      .then(setInsights)
      .catch((reason: Error) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, [filter, offset, refresh]);
  const processing = document?.run.status === 'queued' || document?.run.status === 'running';
  useEffect(() => {
    if (!document || !processing) return;
    const controller = new AbortController();
    const timer = window.setInterval(() => {
      request<DocumentDetail>(`/documents/${document.document_id}`, { signal: controller.signal })
        .then((result) => {
          setDocument(result);
          if (!['queued', 'running'].includes(result.run.status)) setRefresh((old) => old + 1);
        })
        .catch((reason: Error) => {
          if (!controller.signal.aborted) setError(`Mất kết nối khi chờ OCR: ${reason.message}`);
        });
    }, 1200);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [document?.document_id, processing]);
  function updated(value: DocumentDetail) {
    setDocument(value);
    setRefresh((old) => old + 1);
  }
  async function selectDocument(id: string, run?: string) {
    if (dirty) {
      setError('Hãy lưu nháp hoặc bỏ chỉnh sửa trước khi chuyển tài liệu/lần xử lý.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const query = run ? `?run_id=${encodeURIComponent(run)}` : '';
      const result = await request<DocumentDetail>(`/documents/${id}${query}`);
      setDocument(result);
      setActive(result.definitions[0].field_id);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function upload() {
    if (!file || !acknowledged) return;
    if (dirty) {
      setError('Hãy lưu hoặc bỏ chỉnh sửa trước khi tải tài liệu khác.');
      return;
    }
    const maximum = capabilities?.max_upload_bytes ?? 5_242_880;
    if (file.size > maximum) {
      setError(`Ảnh vượt giới hạn ${(maximum / 1024 / 1024).toFixed(0)} MiB.`);
      return;
    }
    const signature = `${file.name}:${file.size}:${file.lastModified}:${type}:${origin}`;
    if (uploadKey.current?.signature !== signature)
      uploadKey.current = { signature, key: crypto.randomUUID() };
    setBusy(true);
    setError('');
    try {
      const query = new URLSearchParams({
        document_type: type,
        data_origin: origin,
        filename: file.name,
      });
      const result = await request<DocumentDetail>(`/documents?${query}`, {
        method: 'POST',
        body: file,
        headers: {
          'Content-Type': 'application/octet-stream',
          'Idempotency-Key': uploadKey.current!.key,
        },
      });
      updated(result);
      setActive(result.definitions[0].field_id);
      uploadKey.current = null;
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="product-workspace">
      <section className="workspace-heading">
        <div>
          <p className="eyebrow">KHÔNG GIAN LÀM VIỆC</p>
          <h1>Từ ảnh nguồn đến dữ liệu đã kiểm tra.</h1>
          <p>Nhận dạng thật, giữ bằng chứng và xuất đúng bản bạn xác nhận.</p>
        </div>
        <span className="pill">
          {capabilities?.ocr_ready ? 'OCR SẴN SÀNG' : 'OCR CHƯA SẴN SÀNG'}
        </span>
      </section>
      {error && (
        <div className="notice" role="alert">
          <p>{error}</p>
          <button
            onClick={() => {
              setError('');
              setRefresh((old) => old + 1);
            }}
          >
            Tải lại danh sách
          </button>
        </div>
      )}
      {insights && (
        <section className="insight-grid" aria-label="Thống kê vận hành">
          <article>
            <strong>{insights.documents}</strong>
            <span>Tài liệu</span>
          </article>
          <article>
            <strong>{insights.completed_runs}</strong>
            <span>Lần xử lý thành công</span>
          </article>
          <article>
            <strong>{insights.confirmed_documents}</strong>
            <span>Tài liệu đã xác nhận</span>
          </article>
          <article>
            <strong>{insights.corrected_fields}</strong>
            <span>Trường đã sửa</span>
          </article>
          <p className="subtle">{insights.notice}</p>
        </section>
      )}
      <section className="upload-panel" aria-label="Tải tài liệu">
        <h2>Thêm tài liệu</h2>
        <div className="upload-grid">
          <label>
            Loại tài liệu
            <select value={type} onChange={(event) => setType(event.target.value)}>
              {schemas.map((schema) => (
                <option key={schema.document_type} value={schema.document_type}>
                  {schema.document_type === 'hoa_don'
                    ? 'Hóa đơn · 5 trường'
                    : 'Đơn đề nghị · 7 trường'}
                </option>
              ))}
            </select>
          </label>
          <label>
            Nguồn dữ liệu
            <select value={origin} onChange={(event) => setOrigin(event.target.value)}>
              <option value="synthetic">Tự tạo · danh tính hư cấu</option>
              <option value="sample">Sample có quyền sử dụng</option>
            </select>
          </label>
          <label>
            Ảnh PNG/JPG một trang
            <input
              type="file"
              accept="image/png,image/jpeg"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <button
            className="primary"
            disabled={busy || !file || !acknowledged || !capabilities?.ocr_ready}
            onClick={() => void upload()}
          >
            {busy ? 'Đang gửi…' : 'Tải lên và nhận dạng'}
          </button>
        </div>
        <label className="data-ack">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
          />
          Tôi xác nhận đây là dữ liệu synthetic/sample hợp lệ, không chứa hồ sơ cá nhân thật.
        </label>
        <p className="subtle">
          Tối đa {((capabilities?.max_upload_bytes ?? 5_242_880) / 1024 / 1024).toFixed(0)} MiB ·
          một trang · chưa hỗ trợ PDF/chữ viết tay.
        </p>
        {!capabilities?.ocr_ready && (
          <p role="status">
            OCR chưa sẵn sàng. Xem hướng dẫn thiết lập Tesseract/model trong README; không có kết
            quả giả thay thế.
          </p>
        )}
      </section>
      <section className="document-list">
        <div className="panel-heading">
          <h2>Tài liệu của phiên làm việc local</h2>
          <label>
            Trạng thái
            <select
              value={filter}
              onChange={(event) => {
                setFilter(event.target.value);
                setOffset(0);
              }}
            >
              <option value="">Tất cả</option>
              {['queued', 'running', 'succeeded', 'failed', 'unavailable'].map((value) => (
                <option key={value} value={value}>
                  {statusLabels[value]}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!list ? (
          <p role="status">Đang tải danh sách…</p>
        ) : !list.items.length ? (
          <p>Chưa có tài liệu phù hợp. Hãy tải ảnh sample đầu tiên.</p>
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Tài liệu</th>
                    <th>Loại</th>
                    <th>Trạng thái</th>
                    <th>Bản lưu</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {list.items.map((item) => (
                    <tr
                      key={item.document_id}
                      className={
                        item.document_id === document?.document_id ? 'selected-document' : ''
                      }
                    >
                      <td>
                        {item.filename}
                        <small>{new Date(item.created_at).toLocaleString('vi-VN')}</small>
                      </td>
                      <td>{item.document_type === 'hoa_don' ? 'Hóa đơn' : 'Đơn đề nghị'}</td>
                      <td>{statusLabels[item.status]}</td>
                      <td>{item.review_status ? statusLabels[item.review_status] : 'Chưa có'}</td>
                      <td>
                        <button
                          disabled={busy}
                          onClick={() => void selectDocument(item.document_id)}
                        >
                          Mở tài liệu
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 10))}>
                Trang trước
              </button>
              <span>
                {offset + 1}–{Math.min(offset + 10, list.total)} / {list.total}
              </span>
              <button disabled={offset + 10 >= list.total} onClick={() => setOffset(offset + 10)}>
                Trang sau
              </button>
            </div>
          </>
        )}
      </section>
      {document && (
        <section className="document-detail">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">ĐANG ĐỐI CHIẾU</p>
              <h2>{document.filename}</h2>
              <p className="subtle">
                Run {document.run.run_id.slice(0, 12)} · {statusLabels[document.run.status]} · SHA{' '}
                {document.input_sha256.slice(0, 12)}
              </p>
            </div>
            <div className="inline-actions">
              <button
                disabled={busy || dirty}
                onClick={() => void selectDocument(document.document_id)}
              >
                Tải bản mới nhất
              </button>
              <button
                disabled={
                  busy || dirty || processing || !document.is_latest_run || !capabilities?.ocr_ready
                }
                onClick={() => {
                  setBusy(true);
                  setError('');
                  void jsonRequest<DocumentDetail>(
                    `/documents/${document.document_id}/runs`,
                    'POST',
                    { expected_run_id: document.latest_run_id },
                  )
                    .then(updated)
                    .catch((reason: Error) => setError(reason.message))
                    .finally(() => setBusy(false));
                }}
              >
                Chạy OCR lại
              </button>
            </div>
          </div>
          {processing && (
            <p className="processing-state" role="status">
              Đang xử lý ảnh bằng OCR thật. Bạn có thể mở lại tài liệu sau; trạng thái được lưu trên
              máy chủ.
            </p>
          )}
          {document.run.error_code && (
            <div className="notice" role="alert">
              Lần xử lý chưa thành công: {document.run.error_code}. Kiểm tra provider/ảnh rồi chọn
              chạy lại.
            </div>
          )}
          <div className="review-workspace">
            <SourcePreview key={document.document_id} document={document} active={active} />
            <ReviewPanel
              key={`${document.document_id}-${document.run.run_id}`}
              document={document}
              onUpdated={updated}
              onDirtyChange={onDirtyChange}
              onFieldChange={setActive}
            />
          </div>
          <HistoryPanel
            document={document}
            onSelectRun={(run) => void selectDocument(document.document_id, run)}
          />
          {document.run.metadata && (
            <details className="run-metadata">
              <summary>Phiên bản và thông tin lần chạy</summary>
              <pre>{JSON.stringify(document.run.metadata, null, 2)}</pre>
            </details>
          )}
        </section>
      )}
    </div>
  );
}
