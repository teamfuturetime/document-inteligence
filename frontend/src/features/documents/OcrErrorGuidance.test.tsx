import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { capabilities, errorDocument, processedDocument } from '../../../e2e/error-fixture';
import { OcrErrorGuidance } from './OcrErrorGuidance';
import { Workspace } from './Workspace';

afterEach(() => vi.unstubAllGlobals());

it.each([
  ['PROVIDER_UNAVAILABLE', 'Tesseract'],
  ['MODEL_HASH_MISMATCH', 'checksum'],
  ['INPUT_CHANGED', 'không khắc phục'],
  ['PROCESSING_INTERRUPTED', 'gián đoạn'],
  ['PROCESSING_TIMEOUT', 'vượt thời gian'],
  ['INVALID_OCR_OUTPUT', 'không hợp lệ'],
  ['PROVIDER_FAILED', 'Engine OCR'],
  ['PROCESSING_FAILED', 'lỗi xử lý'],
  ['INVALID_DOCUMENT', 'Không đọc được'],
  ['UNSUPPORTED_MEDIA_TYPE', 'PNG/JPEG hoặc PDF một trang'],
  ['INVALID_PDF', 'Không đọc được PDF'],
  ['PDF_ENCRYPTED', 'PDF một trang không mã hóa'],
  ['PDF_PAGE_COUNT', 'PDF phải có đúng một trang'],
  ['FILE_TOO_LARGE', 'dung lượng'],
  ['IMAGE_TOO_LARGE', 'điểm ảnh'],
  ['UNSUPPORTED_SCHEMA', 'Loại tài liệu'],
  ['PRIVATE /secret stderr', 'Chưa xác định'],
  ['__proto__', 'Chưa xác định'],
])('explains %s with a safe atomic alert', (code, copy) => {
  render(<OcrErrorGuidance code={code} requestId="request-49" />);
  expect(screen.getByRole('alert')).toHaveTextContent(copy);
  expect(screen.getByRole('alert')).toHaveAttribute('aria-atomic', 'true');
  expect(screen.getByText('request-49')).toBeVisible();
  expect(screen.getByRole('alert')).not.toHaveTextContent('PRIVATE');
});

it('hides unsafe request identifiers', () => {
  render(<OcrErrorGuidance code="unknown" requestId="/private/path" />);
  expect(screen.getByRole('alert')).not.toHaveTextContent('/private/path');
});

it.each([
  { historical: false, reject: false },
  { historical: true, reject: false },
  { historical: false, reject: true },
])('keeps retry guarded and explicit: %j', async ({ historical, reject }) => {
  const document = { ...errorDocument(), is_latest_run: !historical };
  const writes = vi.fn();
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options?: RequestInit) => {
      const path = new URL(url, 'http://localhost').pathname;
      let value: unknown = document;
      if (path.endsWith('/document-schemas')) value = [];
      else if (path.endsWith('/insights')) value = { documents: 1 };
      else if (path.endsWith('/history')) value = { runs: [], events: [] };
      else if (path.endsWith('/documents'))
        value = { items: [document], total: 1, offset: 0, limit: 10 };
      else if (path.endsWith('/runs')) {
        writes(JSON.parse(options?.body as string));
        if (reject)
          return new Response(
            JSON.stringify({
              error: {
                code: 'PROVIDER_UNAVAILABLE',
                message: '/private/native stderr',
                request_id: 'req-49',
              },
            }),
            { status: 503, headers: { 'Content-Type': 'application/json' } },
          );
        value = processedDocument();
      }
      return new Response(JSON.stringify(value), {
        headers: { 'Content-Type': 'application/json' },
      });
    }),
  );
  render(<Workspace capabilities={capabilities} onUnsavedChange={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Mở tài liệu' }));
  await screen.findByText(/OCR vượt thời gian/);
  expect(writes).not.toHaveBeenCalled();
  const retry = screen.getByRole('button', { name: 'Chạy OCR lại' });
  expect(retry.hasAttribute('disabled')).toBe(historical);
  if (!historical) {
    retry.focus();
    expect(retry).toHaveFocus();
    fireEvent.click(retry);
    if (reject) {
      await screen.findByText('req-49');
      expect(screen.getByRole('alert')).toHaveTextContent('Tesseract');
      expect(screen.getByRole('alert')).not.toHaveTextContent('/private');
      expect(screen.getByText(/Run old/)).toBeVisible();
    } else await screen.findByRole('textbox', { name: /Đơn vị bán hàng/ });
    expect(writes).toHaveBeenCalledExactlyOnceWith({ expected_run_id: 'old' });
  }
});
