import type { components } from '../../lib/api.generated';

export type DocumentDetail = components['schemas']['DocumentDetail'];
export type DocumentList = components['schemas']['DocumentList'];
export type DocumentHistory = components['schemas']['DocumentHistory'];
export type ProductSchema = components['schemas']['ProductSchema'];
export type ProductInsights = components['schemas']['ProductInsights'];
export type ReviewRequest = components['schemas']['ReviewRequest'];
export type ProductFieldId = components['schemas']['FieldDefinition']['field_id'];

export class APIError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
  ) {
    super(message);
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new APIError(
      response.status,
      payload?.error?.code ?? 'NETWORK_ERROR',
      payload?.error?.message ?? `Yêu cầu thất bại (HTTP ${response.status}).`,
      payload?.error?.request_id,
    );
  }
  return response.json() as Promise<T>;
}

export function jsonRequest<T>(
  path: string,
  method: string,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return request(path, {
    signal,
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function downloadExport(document: DocumentDetail): Promise<void> {
  if (!document.review) throw new Error('Chưa có bản review.');
  const query = new URLSearchParams({
    run_id: document.run.run_id,
    revision: String(document.review.revision),
  });
  const response = await fetch(`/api/v1/documents/${document.document_id}/export?${query}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new APIError(
      response.status,
      payload?.error?.code ?? 'EXPORT_FAILED',
      payload?.error?.message ?? 'Không xuất được JSON.',
    );
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = window.document.createElement('a');
  anchor.href = url;
  anchor.download = `document-${document.document_id}-r${document.review.revision}.json`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const statusLabels: Record<string, string> = {
  queued: 'Đang chờ',
  running: 'Đang nhận dạng',
  succeeded: 'Đã xử lý',
  failed: 'Xử lý lỗi',
  unavailable: 'OCR chưa sẵn sàng',
  draft: 'Bản nháp',
  confirmed: 'Đã xác nhận',
};
