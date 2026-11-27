import { useContext, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { ReviewIdentityContext, reviewDraftPrefix } from '../../lib/reviewDrafts';
import { getSessionSnapshot } from '../../lib/session';
import { APIError, downloadExport, jsonRequest, request, statusLabels } from './api';
import type { DocumentDetail, ProductFieldId, ReviewRequest } from './api';

type Changes = ReviewRequest['fields'];

// Bounded recovery of changed review fields; never restores server authority.
function draftPrefix(document: DocumentDetail, identity: string) {
  return reviewDraftPrefix(identity, document.document_id, document.run.run_id);
}
function recover(document: DocumentDetail, identity: string): Changes {
  try {
    const prefix = draftPrefix(document, identity);
    const legacyKey = prefix.slice(0, -1);
    const legacy = sessionStorage.getItem(legacyKey);
    if (legacy) {
      // Keep the old entry unless durable storage has accepted the copy.
      localStorage.setItem(prefix + 'legacy', legacy);
      sessionStorage.removeItem(legacyKey);
    }
    const candidates = Object.keys(localStorage).filter((key) => key.startsWith(prefix));
    const values = candidates.map((key) => {
      try {
        const raw = localStorage.getItem(key) ?? 'null';
        const parsed = JSON.parse(raw);
        if (!parsed || !Number.isFinite(parsed.at) || Date.now() - parsed.at > 86_400_000) {
          localStorage.removeItem(key);
          return null;
        }
        return { ...parsed, key, raw };
      } catch {
        return null;
      }
    });
    const value = values
      .filter((item) => item && Number.isFinite(item.at) && Date.now() - item.at <= 86_400_000)
      .sort((a, b) => b.at - a.at)[0];
    if (
      !value ||
      !Number.isFinite(value.at) ||
      Date.now() - value.at > 86_400_000 ||
      !value.fields ||
      typeof value.fields !== 'object'
    )
      return {};
    const result: Changes = {};
    for (const definition of document.definitions) {
      const field = value.fields[definition.field_id];
      if (
        field &&
        typeof field.is_reviewed === 'boolean' &&
        (field.reviewed_value === null || typeof field.reviewed_value === 'string')
      )
        result[definition.field_id] = field;
    }
    return result;
  } catch {
    return {};
  }
}

export function ReviewPanel({
  document,
  onUpdated,
  onDirtyChange,
  onFieldChange,
  backendReady = true,
}: {
  document: DocumentDetail;
  onUpdated: (value: DocumentDetail) => void;
  onDirtyChange: (value: boolean) => void;
  onFieldChange: (value: string) => void;
  backendReady?: boolean;
}) {
  const identity = useContext(ReviewIdentityContext);
  const [sessionRevision] = useState(() => getSessionSnapshot().revision);
  const [base, setBase] = useState(document);
  const [changes, updateChanges] = useState<Changes>(() => recover(document, identity));
  const changesRef = useRef(changes);
  const baseRef = useRef(base);
  const mounted = useRef(true);
  const inFlight = useRef(false);
  const [saving, setSaving] = useState(false);
  const [storageError, setStorageError] = useState(false);
  const [storageKey] = useState(() => {
    try {
      // sessionStorage is cloned by window.open/duplicate-tab. Each mounted
      // editor needs its own key, including when its opener has pending edits.
      return draftPrefix(document, identity) + crypto.randomUUID();
    } catch {
      return null;
    }
  });
  function setChanges(next: Changes | ((old: Changes) => Changes)) {
    const value = typeof next === 'function' ? next(changesRef.current) : next;
    changesRef.current = value;
    updateChanges(value);
    if (getSessionSnapshot().revision !== sessionRevision) return;
    try {
      if (!storageKey) throw new Error('Storage unavailable');
      if (Object.keys(value).length)
        localStorage.setItem(storageKey, JSON.stringify({ at: Date.now(), fields: value }));
      else {
        localStorage.removeItem(storageKey);
        // Recovery never transfers ownership of another editor's key.
      }
      setStorageError(false);
    } catch {
      setStorageError(true);
    }
  }
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<Error | null>(() =>
    Object.keys(changes).length
      ? new APIError(
          409,
          'RECOVERED_DRAFT',
          'Đã khôi phục bản nháp. Hãy đối chiếu máy chủ trước khi lưu.',
        )
      : null,
  );
  const [conflict, setConflict] = useState<DocumentDetail | null>(null);
  const operations = useRef(new AbortController());
  const operationRevision = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    operations.current = controller;
    ++operationRevision.current;
    inFlight.current = false;
    setSaving(false);
    setBusy(false);
    return () => {
      ++operationRevision.current;
      controller.abort();
    };
  }, [backendReady]);
  const headingId = useId();
  const panelRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const conflictRef = useRef<HTMLDivElement>(null);
  const exportRef = useRef<HTMLButtonElement>(null);
  const confirmFocusOrigin = useRef<Element | null>(null);
  const [editorFocus, setEditorFocus] = useState<{ origin: Element | null } | null>(null);
  function mayRestoreFocus(origin: Element | null) {
    if (!origin) return false;
    const active = window.document.activeElement;
    const lostOrigin = !origin.isConnected || origin.matches(':disabled');
    return active === origin || (active === window.document.body && lostOrigin);
  }
  function focusEditor(origin = window.document.activeElement) {
    setEditorFocus({ origin });
  }
  useLayoutEffect(() => {
    if (!editorFocus || getSessionSnapshot().revision !== sessionRevision) return;
    if (!mayRestoreFocus(editorFocus.origin)) return;
    panelRef.current?.querySelector<HTMLElement>('[id^="field-"]:not(:disabled)')?.focus();
  }, [editorFocus, sessionRevision]);
  useEffect(() => {
    titleRef.current?.focus();
  }, []);
  useEffect(() => {
    // Background autosave must not interrupt someone still typing.
    if (error && !['INPUT', 'TEXTAREA'].includes(window.document.activeElement?.tagName ?? ''))
      errorRef.current?.focus();
  }, [error]);
  useEffect(() => {
    if (conflict) conflictRef.current?.focus();
  }, [conflict]);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (document === baseRef.current) return;
    // Parent refreshes must never discard local edits or race a save ACK.
    if (inFlight.current || Object.keys(changesRef.current).length) return;
    baseRef.current = document;
    setBase(document);
    setConflict(null);
  }, [document]);
  const dirty = Object.keys(changes).length > 0 || saving;
  const [resumeRequired, setResumeRequired] = useState(false);
  useEffect(() => {
    if (!backendReady && dirty) setResumeRequired(true);
  }, [backendReady, dirty]);
  useEffect(() => {
    onDirtyChange(dirty);
  }, [dirty, onDirtyChange]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  const review = base.review;
  useEffect(() => {
    if (busy || review?.review_status !== 'confirmed') return;
    const origin = confirmFocusOrigin.current;
    confirmFocusOrigin.current = null;
    if (getSessionSnapshot().revision === sessionRevision && mayRestoreFocus(origin))
      exportRef.current?.focus();
  }, [busy, review?.review_status, sessionRevision]);
  const editable = base.is_latest_run && !!review && !busy;
  useEffect(() => {
    if (
      !dirty ||
      !backendReady ||
      resumeRequired ||
      saving ||
      busy ||
      error ||
      conflict ||
      !base.is_latest_run ||
      base.review?.review_status !== 'draft'
    )
      return;
    const timer = setTimeout(() => {
      void save();
    }, 800);
    return () => clearTimeout(timer);
  });
  const values = review?.effective_data ?? {};
  const issues = review?.validation_issues ?? [];
  function valueOf(key: ProductFieldId): string {
    const changed = changes[key];
    if (changed?.is_reviewed) return String(changed.reviewed_value ?? '');
    if (changed)
      return String(
        (base.run.fields ?? []).find((field) => field.field_id === key)?.normalized_value ?? '',
      );
    return String(values[key] ?? '');
  }
  function change(key: ProductFieldId, value: string | null, reviewed = true) {
    setChanges((old) => ({ ...old, [key]: { is_reviewed: reviewed, reviewed_value: value } }));
    setMessage('Có thay đổi chưa lưu.');
    // Failed/ambiguous requests require explicit retry; 409 requires comparison.
  }
  async function act(operation: (signal: AbortSignal) => Promise<void>) {
    if (!backendReady || busy || saving) return;
    const sequence = ++operationRevision.current;
    const signal = AbortSignal.any([operations.current.signal, AbortSignal.timeout(15000)]);
    const current = () => mounted.current && sequence === operationRevision.current;
    setBusy(true);
    setMessage('');
    try {
      await operation(signal);
      if (current()) setError(null);
    } catch (reason) {
      // A failed/canceled comparison never grants permission to save a
      // recovered/conflicted draft before the user actually compares it.
      if (current() && !(error instanceof APIError && error.status === 409))
        setError(reason as Error);
    } finally {
      if (current()) setBusy(false);
    }
  }
  async function save(manual = false) {
    if (
      !review ||
      !backendReady ||
      (!manual && resumeRequired) ||
      getSessionSnapshot().revision !== sessionRevision ||
      inFlight.current ||
      busy ||
      !editable ||
      conflict ||
      !Object.keys(changesRef.current).length ||
      (error instanceof APIError && error.status === 409)
    )
      return;
    setResumeRequired(false);
    const sequence = ++operationRevision.current;
    const signal = AbortSignal.any([operations.current.signal, AbortSignal.timeout(15000)]);
    const current = () => mounted.current && sequence === operationRevision.current;
    const focusOrigin = window.document.activeElement;
    const snapshot = changesRef.current;
    inFlight.current = true;
    setSaving(true);
    setError(null);
    try {
      const result = await jsonRequest<DocumentDetail>(
        `/documents/${base.document_id}/review`,
        'PUT',
        {
          run_id: base.run.run_id,
          expected_revision: review.revision,
          expected_status: review.review_status,
          fields: snapshot,
        },
        signal,
      );
      if (!current() || signal.aborted) return;
      baseRef.current = result;
      setBase(result);
      setChanges(
        (latest) =>
          Object.fromEntries(
            Object.entries(latest).filter(
              ([key, value]) => value !== snapshot[key as ProductFieldId],
            ),
          ) as Changes,
      );
      onUpdated(result);
      setMessage('Đã lưu nháp trên máy chủ.');
      if (manual) focusEditor(focusOrigin);
    } catch (reason) {
      if (current()) setError(reason as Error);
    } finally {
      if (current()) {
        inFlight.current = false;
        setSaving(false);
      }
    }
  }
  return (
    <section ref={panelRef} className="review-panel" aria-label="Kiểm tra và sửa kết quả">
      <div className="panel-heading">
        <div>
          <h2 ref={titleRef} tabIndex={-1} id={headingId}>
            Kiểm tra dữ liệu
          </h2>
          <p className="subtle">
            {review
              ? `Revision ${review.revision} · ${statusLabels[review.review_status]}`
              : statusLabels[base.run.status]}
          </p>
        </div>
        <span className="pill">{base.document_type === 'hoa_don' ? 'HÓA ĐƠN' : 'ĐƠN ĐỀ NGHỊ'}</span>
      </div>
      <p className="confidence-note">
        Điểm OCR là tín hiệu heuristic từ vùng chữ, chưa phải xác suất trường đúng. Hãy kiểm tra ảnh
        trước khi xác nhận.
      </p>
      {!base.is_latest_run && (
        <p className="fixture-banner">
          Đang xem lần xử lý cũ, chỉ đọc. Chọn lần mới nhất để tiếp tục review.
        </p>
      )}
      {error && (
        <div
          ref={errorRef}
          tabIndex={-1}
          role="alert"
          aria-label="Lỗi lưu bản rà soát"
          aria-atomic="true"
          className="notice"
        >
          <strong>{error.message}</strong>
          {error instanceof APIError && (
            <p>
              Mã: {error.code}
              {error.requestId ? ` · Yêu cầu: ${error.requestId}` : ''}
            </p>
          )}
          {error instanceof APIError && error.status === 409 && (
            <button
              disabled={!backendReady || busy}
              onClick={() =>
                void act(async (signal) => {
                  const result = await request<DocumentDetail>(`/documents/${base.document_id}`, {
                    signal,
                  });
                  signal.throwIfAborted();
                  setConflict(result);
                })
              }
            >
              Đối chiếu bản mới
            </button>
          )}
        </div>
      )}
      {storageError && (
        <p role="alert">
          Không thể giữ bản nháp trong trình duyệt. Hãy lưu hoặc sao chép chỉnh sửa trước khi rời
          trang.
        </p>
      )}
      {review?.review_status === 'confirmed' && (
        <p>Bản đã xác nhận không tự động lưu. Chỉnh sửa rồi bấm Lưu nháp để mở lại review.</p>
      )}
      {conflict && (
        <div
          ref={conflictRef}
          tabIndex={-1}
          role="region"
          aria-label="Đối chiếu chỉnh sửa với máy chủ"
          className="conflict-box"
        >
          <h3>Bản trên máy chủ và chỉnh sửa của bạn</h3>
          <p>Chỉnh sửa của bạn vẫn được giữ. Kiểm tra từng trường trước khi dùng revision mới.</p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Trường</th>
                  <th>Bạn đang sửa</th>
                  <th>Máy chủ</th>
                </tr>
              </thead>
              <tbody>
                {base.definitions.map((definition) => (
                  <tr key={definition.field_id}>
                    <th>{definition.label}</th>
                    <td>{valueOf(definition.field_id) || '(trống)'}</td>
                    <td>
                      {String(conflict.review?.effective_data[definition.field_id] ?? '(trống)')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {conflict.run.run_id === base.run.run_id && conflict.review && (
            <button
              onClick={() => {
                setBase(conflict);
                baseRef.current = conflict;
                setConflict(null);
                setError(null);
                setMessage('Đã đối chiếu. Chỉnh sửa vẫn chưa lưu; hãy lưu lại nếu muốn áp dụng.');
                focusEditor();
              }}
            >
              Giữ chỉnh sửa, dùng revision mới
            </button>
          )}
          <button
            onClick={() => {
              onUpdated(conflict);
              baseRef.current = conflict;
              setBase(conflict);
              setConflict(null);
              setError(null);
              setChanges({});
              focusEditor();
            }}
          >
            Bỏ chỉnh sửa, tải bản máy chủ
          </button>
        </div>
      )}
      {issues.length > 0 && (
        <div
          className="validation-summary"
          role="status"
          aria-label="Kiểm tra tính hợp lệ"
          aria-atomic="true"
        >
          <strong>{issues.length} trường cần kiểm tra</strong>
          <p>Bản nháp được phép lưu khi còn thiếu hoặc sai. Cần sửa các lỗi trước khi xác nhận.</p>
        </div>
      )}
      <div className="product-fields">
        {base.definitions.map((definition) => {
          const key = definition.field_id;
          const prediction = (base.run.fields ?? []).find((field) => field.field_id === key);
          const fieldIssues = issues.filter((issue) => issue.field_path === key);
          const score = prediction?.confidence.ocr_score;
          return (
            <article key={key} className="product-field" onFocus={() => onFieldChange(key)}>
              <div className="field-label-row">
                <label htmlFor={`field-${key}`}>{definition.label} *</label>
                <button
                  className="text-button"
                  aria-label={`Xem vùng nguồn: ${definition.label}`}
                  onClick={() => onFieldChange(key)}
                  type="button"
                >
                  Xem vùng nguồn
                </button>
              </div>
              {key === 'request_content' ? (
                <textarea
                  id={`field-${key}`}
                  rows={4}
                  value={valueOf(key)}
                  disabled={!editable}
                  aria-invalid={fieldIssues.length > 0}
                  aria-describedby={`help-${key}`}
                  onChange={(event) => change(key, event.target.value || null)}
                />
              ) : (
                <input
                  id={`field-${key}`}
                  value={valueOf(key)}
                  disabled={!editable}
                  inputMode={definition.value_type === 'integer' ? 'numeric' : undefined}
                  aria-invalid={fieldIssues.length > 0}
                  aria-describedby={`help-${key}`}
                  onChange={(event) => change(key, event.target.value || null)}
                />
              )}
              <div id={`help-${key}`} className="field-help">
                <span>Máy: {String(prediction?.normalized_value ?? 'Không trích xuất được')}</span>
                <span>
                  {score == null
                    ? 'Chưa có điểm OCR'
                    : `OCR nhỏ nhất: ${(score * 100).toFixed(0)}/100`}
                </span>
                {prediction?.confidence.reason_codes?.includes('AMBIGUOUS_CANDIDATES') && (
                  <span>Nhiều ứng viên mâu thuẫn; máy đã để trống.</span>
                )}
                {prediction?.confidence.reason_codes?.includes('LOW_OCR_EVIDENCE') && (
                  <span>Điểm OCR thấp; máy đã để trống để bạn đối chiếu.</span>
                )}
                {fieldIssues.map((issue) => (
                  <span className="field-error" key={issue.code}>
                    {issue.message}
                  </span>
                ))}
              </div>
              {review && (
                <div className="field-controls">
                  <label>
                    <input
                      type="checkbox"
                      disabled={!editable}
                      checked={
                        changes[key]?.is_reviewed ?? review.fields[key]?.is_reviewed ?? false
                      }
                      onChange={(event) =>
                        change(
                          key,
                          event.target.checked ? valueOf(key) || null : null,
                          event.target.checked,
                        )
                      }
                    />
                    Đã đối chiếu trường này
                  </label>
                  <button type="button" disabled={!editable} onClick={() => change(key, null)}>
                    Xóa giá trị
                  </button>
                  <button
                    type="button"
                    disabled={!editable}
                    onClick={() => change(key, null, false)}
                  >
                    Dùng dự đoán máy
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>
      <div className="review-actions">
        <button
          className="primary"
          disabled={
            !backendReady ||
            !editable ||
            !dirty ||
            saving ||
            (error instanceof APIError && error.status === 409)
          }
          onClick={() => void save(true)}
        >
          {busy ? 'Đang xử lý…' : 'Lưu nháp'}
        </button>
        <button
          disabled={!editable || !dirty || saving}
          onClick={() => {
            setChanges({});
            setMessage('Đã bỏ chỉnh sửa chưa lưu.');
            focusEditor();
          }}
        >
          Bỏ chỉnh sửa
        </button>
        <button
          disabled={
            !editable ||
            !backendReady ||
            saving ||
            dirty ||
            issues.length > 0 ||
            review?.review_status === 'confirmed'
          }
          onClick={() => {
            const focusOrigin = window.document.activeElement;
            void act(async (signal) => {
              const result = await jsonRequest<DocumentDetail>(
                `/documents/${base.document_id}/confirm`,
                'POST',
                {
                  run_id: base.run.run_id,
                  expected_revision: review!.revision,
                },
                signal,
              );
              signal.throwIfAborted();
              confirmFocusOrigin.current = focusOrigin;
              onUpdated(result);
              setMessage('Đã xác nhận bản lưu. Có thể xuất JSON.');
            });
          }}
        >
          Xác nhận bản lưu
        </button>
        <button
          ref={exportRef}
          disabled={
            !backendReady || !editable || saving || dirty || review?.review_status !== 'confirmed'
          }
          onClick={() =>
            void act(async (signal) => {
              await downloadExport(base, signal);
              signal.throwIfAborted();
              setMessage('Đã tải JSON từ bản xác nhận trên máy chủ.');
            })
          }
        >
          Xuất JSON đã xác nhận
        </button>
      </div>
      <p
        role="status"
        aria-label="Trạng thái lưu"
        aria-live="polite"
        aria-atomic="true"
        className="save-status"
      >
        {!backendReady
          ? 'Mất kết nối hoặc backend chưa sẵn sàng. Chỉnh sửa vẫn được giữ.'
          : resumeRequired && dirty
            ? 'Đã kết nối lại. Hãy bấm Lưu nháp hoặc đối chiếu trước khi tiếp tục; không tự gửi lại.'
            : saving
              ? 'Đang lưu nháp…'
              : error
                ? 'Lưu thất bại. Chỉnh sửa được giữ; hãy thử Lưu nháp hoặc đối chiếu khi xung đột.'
                : busy
                  ? 'Đang trao đổi với máy chủ…'
                  : dirty
                    ? 'Chưa lưu. Tự động lưu sau khi ngừng nhập.'
                    : message || 'Không có thay đổi chưa lưu.'}
      </p>
    </section>
  );
}
