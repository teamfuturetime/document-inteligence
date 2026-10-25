import { useEffect, useState } from 'react';
import { request, statusLabels } from './api';
import type { DocumentDetail, DocumentHistory } from './api';

const actions: Record<string, string> = {
  uploaded: 'Tải tài liệu',
  processed: 'Đã xử lý AI',
  review_saved: 'Lưu nháp',
  confirmed: 'Xác nhận',
  exported: 'Xuất JSON',
  interrupted: 'Xử lý bị gián đoạn',
  processing_failed: 'Xử lý thất bại',
  reprocess_requested: 'Yêu cầu xử lý lại',
};

export function HistoryPanel({
  document,
  onSelectRun,
}: {
  document: DocumentDetail;
  onSelectRun: (run: string) => void;
}) {
  const [history, setHistory] = useState<DocumentHistory | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    request<DocumentHistory>(`/documents/${document.document_id}/history`, {
      signal: controller.signal,
    })
      .then(setHistory)
      .catch((reason: Error) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, [document]);
  return (
    <details
      className="history-panel"
      onToggle={(event) => {
        if (event.currentTarget.open) {
          setError('');
          void request<DocumentHistory>(`/documents/${document.document_id}/history`)
            .then(setHistory)
            .catch((reason: Error) => setError(reason.message));
        }
      }}
    >
      <summary>Lịch sử xử lý và thay đổi</summary>
      {error && <p role="alert">{error}</p>}
      {history && (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Lần xử lý</th>
                  <th>Trạng thái</th>
                  <th>Thời gian</th>
                  <th>Xem</th>
                </tr>
              </thead>
              <tbody>
                {history.runs.map((run) => (
                  <tr key={run.run_id}>
                    <td>
                      <code>{run.run_id.slice(0, 10)}</code>
                      {run.run_id === document.latest_run_id ? ' · mới nhất' : ''}
                    </td>
                    <td>{statusLabels[run.status]}</td>
                    <td>{new Date(run.created_at).toLocaleString('vi-VN')}</td>
                    <td>
                      <button
                        disabled={run.run_id === document.run.run_id}
                        onClick={() => onSelectRun(run.run_id)}
                      >
                        Xem bản này
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ol className="event-list">
            {history.events.map((event, index) => (
              <li key={`${event.occurred_at}-${index}`}>
                <strong>{actions[event.action] ?? event.action}</strong> ·{' '}
                {new Date(event.occurred_at).toLocaleString('vi-VN')}
                {event.revision != null ? ` · revision ${event.revision}` : ''}
              </li>
            ))}
          </ol>
          <p className="subtle">
            Không có tài khoản đăng nhập; hệ thống không tự gán danh tính người sửa.
          </p>
        </>
      )}
    </details>
  );
}
