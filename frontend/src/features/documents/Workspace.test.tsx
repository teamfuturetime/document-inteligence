import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Workspace } from './Workspace';
import type { DocumentDetail } from './api';

function document(id: string, status: DocumentDetail['run']['status']): DocumentDetail {
  return {
    document_id: id,
    document_type: 'hoa_don',
    filename: `${id}.png`,
    data_origin: 'synthetic',
    input_sha256: 'a'.repeat(64),
    image_width: 100,
    image_height: 100,
    created_at: '2026-11-09T00:00:00Z',
    latest_run_id: `run-${id}`,
    status,
    image_url: `/api/v1/documents/${id}/image`,
    is_latest_run: true,
    review: null,
    definitions: [
      { field_id: 'seller_name', label: 'Đơn vị bán hàng', value_type: 'text', required: true },
    ],
    run: { run_id: `run-${id}`, status, created_at: '2026-11-09T00:00:00Z' },
  };
}

function response(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    headers: { 'Content-Type': 'application/json' },
  });
}

function deferredResponse() {
  let resolve!: (value: Response) => void;
  const promise = new Promise<Response>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function mockWorkspace(sendUpload?: (options?: RequestInit) => Promise<Response>) {
  const queued = document('invoice-a', 'queued');
  const completed = document('invoice-b', 'succeeded');
  const poll = vi.fn<(options?: RequestInit) => Promise<Response>>();
  let openedA = false;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options?: RequestInit) => {
      const { pathname, searchParams } = new URL(path, 'http://localhost');
      switch (pathname) {
        case '/api/v1/document-schemas':
          return response([]);
        case '/api/v1/insights':
          return response({ documents: 2 });
        case '/api/v1/documents':
          if (options?.method === 'POST' && sendUpload) return sendUpload(options);
          return response({ items: [queued, completed], total: 2, offset: 0, limit: 10 });
        case '/api/v1/documents/invoice-a':
          if (openedA || searchParams.has('run_id')) return poll(options);
          openedA = true;
          return response(queued);
        case '/api/v1/documents/invoice-b':
          return response(completed);
        case '/api/v1/documents/invoice-a/history':
        case '/api/v1/documents/invoice-b/history':
        case '/api/v1/documents/uploaded/history':
          return response({ runs: [], events: [] });
        default:
          throw new Error(`Unexpected request: ${path}`);
      }
    }),
  );
  const editor = (backendReady = true) => (
    <Workspace
      backendReady={backendReady}
      capabilities={{
        features: {},
        max_upload_bytes: 5_242_880,
        model_benchmark_status: 'not_measured',
        ocr_ready: true,
        provider_mode: 'tesseract',
        supported_schemas: [],
        upload_media_types: ['image/png', 'image/jpeg'],
      }}
      onUnsavedChange={vi.fn()}
    />
  );
  const view = render(editor());
  return Object.assign(poll, { setReady: (ready: boolean) => view.rerender(editor(ready)) });
}

async function open(id: string) {
  await act(async () => {
    const row = screen.getByRole('row', { name: new RegExp(`${id}\\.png`) });
    fireEvent.click(within(row).getByRole('button', { name: 'Mở tài liệu' }));
  });
}

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('Theo dõi trạng thái OCR', () => {
  it.each(['upload', 'OCR retry'])(
    'ignores an interrupted %s ACK while its explicit replacement is pending',
    async (kind) => {
      vi.useFakeTimers();
      const first = deferredResponse();
      const second = deferredResponse();
      const send = vi
        .fn<(options?: RequestInit) => Promise<Response>>()
        .mockReturnValueOnce(first.promise)
        .mockReturnValueOnce(second.promise);
      const workspace = mockWorkspace(kind === 'upload' ? send : undefined);
      await advance(0);
      if (kind === 'upload') {
        fireEvent.change(screen.getByLabelText('Ảnh PNG/JPG một trang'), {
          target: { files: [new File(['sample'], 'synthetic.png', { type: 'image/png' })] },
        });
        fireEvent.click(screen.getByRole('checkbox', { name: /Tôi xác nhận/ }));
      } else {
        await open('invoice-b');
        const original = vi.mocked(fetch).getMockImplementation()!;
        vi.mocked(fetch).mockImplementation((path, options) =>
          String(path).endsWith('/runs') ? send(options) : original(path, options),
        );
      }
      const action = () =>
        screen.getByRole('button', {
          name: kind === 'upload' ? /Tải lên và nhận dạng|Đang gửi/ : 'Chạy OCR lại',
        });
      fireEvent.click(action());
      expect(send).toHaveBeenCalledTimes(1);
      workspace.setReady(false);
      expect(send.mock.calls[0][0]?.signal?.aborted).toBe(true);
      workspace.setReady(true);
      expect(action()).toBeEnabled();
      fireEvent.click(action());
      expect(send).toHaveBeenCalledTimes(2);
      await act(async () => first.resolve(response(document('stale-ack', 'succeeded'))));
      expect(action()).toBeDisabled();
      expect(screen.queryByRole('heading', { name: 'stale-ack.png' })).not.toBeInTheDocument();
      await act(async () => second.resolve(response(document('invoice-b', 'succeeded'))));
      expect(screen.getByRole('heading', { name: 'invoice-b.png' })).toBeVisible();
      if (kind === 'upload')
        expect(new Headers(send.mock.calls[0][0]?.headers).get('Idempotency-Key')).toBe(
          new Headers(send.mock.calls[1][0]?.headers).get('Idempotency-Key'),
        );
    },
  );
  it('does not let an older selection clear the busy state of a newer pending selection', async () => {
    vi.useFakeTimers();
    mockWorkspace();
    await advance(0);
    const original = vi.mocked(fetch).getMockImplementation()!;
    const first = deferredResponse();
    const second = deferredResponse();
    vi.mocked(fetch).mockImplementation((path, options) => {
      if (String(path).endsWith('/invoice-a')) return first.promise;
      if (String(path).endsWith('/invoice-b')) return second.promise;
      return original(path, options);
    });
    const buttons = screen.getAllByRole('button', { name: 'Mở tài liệu' });
    act(() => {
      fireEvent.click(buttons[0]);
      fireEvent.click(buttons[1]);
    });
    await act(async () => first.resolve(response(document('invoice-a', 'succeeded'))));
    expect(buttons[1]).toBeDisabled();
    await act(async () => second.resolve(response(document('invoice-b', 'succeeded'))));
    expect(screen.getByRole('heading', { name: 'invoice-b.png' })).toBeVisible();
  });
  it('chờ phản hồi trước khi gửi tiếp và dừng khi OCR hoàn tất', async () => {
    vi.useFakeTimers();
    const poll = mockWorkspace();
    const pending = deferredResponse();
    poll.mockReturnValue(pending.promise);
    await advance(0);
    await open('invoice-a');

    await advance(3600);
    expect(poll).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/Tài liệu đang chờ xử lý/)).toBeVisible();

    await act(async () => pending.resolve(response(document('invoice-a', 'succeeded'))));
    expect(screen.queryByText(/Tài liệu đang chờ xử lý/)).not.toBeInTheDocument();
    await advance(5000);
    expect(poll).toHaveBeenCalledTimes(1);
  });

  it('giãn thời gian thử lại khi mất kết nối và xóa cảnh báo khi có phản hồi', async () => {
    vi.useFakeTimers();
    const poll = mockWorkspace();
    poll
      .mockRejectedValueOnce(new TypeError('Network offline'))
      .mockResolvedValueOnce(response(document('invoice-a', 'running')))
      .mockResolvedValueOnce(response(document('invoice-a', 'succeeded')));
    await advance(0);
    await open('invoice-a');

    await advance(1200);
    expect(screen.getByRole('alert')).toHaveTextContent('Chưa cập nhật được trạng thái OCR');
    await advance(2399);
    expect(poll).toHaveBeenCalledTimes(1);

    await advance(1);
    expect(poll).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText(/OCR đang nhận dạng tài liệu/)).toBeVisible();

    await advance(1200);
    expect(poll).toHaveBeenCalledTimes(3);
    expect(screen.queryByText(/OCR đang nhận dạng tài liệu/)).not.toBeInTheDocument();
  });

  it('bỏ phản hồi đến muộn sau khi người dùng mở tài liệu khác', async () => {
    vi.useFakeTimers();
    const poll = mockWorkspace();
    const pending = deferredResponse();
    poll.mockReturnValue(pending.promise);
    await advance(0);
    await open('invoice-a');
    await advance(1200);
    const signal = poll.mock.calls[0][0]?.signal;

    await open('invoice-b');
    expect(signal?.aborted).toBe(true);
    await act(async () => pending.resolve(response(document('invoice-a', 'succeeded'))));
    expect(screen.getByRole('heading', { name: 'invoice-b.png' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'invoice-a.png' })).not.toBeInTheDocument();
    await advance(5000);
    expect(poll).toHaveBeenCalledTimes(1);
  });
});

describe('Gửi lại upload', () => {
  const select = (file: File) =>
    fireEvent.change(screen.getByLabelText('Ảnh PNG/JPG một trang'), {
      target: { files: [file] },
    });

  async function send() {
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Tải lên và nhận dạng|Thử tải lại/ }));
    });
  }

  it('giữ khóa khi gửi lại cùng file sau lỗi mạng và bỏ chọn file khi thành công', async () => {
    const sendUpload = vi
      .fn<(options?: RequestInit) => Promise<Response>>()
      .mockRejectedValueOnce(new TypeError('Network offline'))
      .mockResolvedValueOnce(response(document('uploaded', 'succeeded')));
    mockWorkspace(sendUpload);
    select(new File(['a'], 'sample.png', { type: 'image/png' }));
    fireEvent.click(screen.getByRole('checkbox', { name: /Tôi xác nhận/ }));

    await send();
    expect(screen.getByRole('alert')).toHaveTextContent('Mất kết nối khi tải tệp');
    expect(screen.getByRole('button', { name: 'Thử tải lại' })).toBeEnabled();
    await send();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    const keys = sendUpload.mock.calls.map(([options]) =>
      new Headers(options?.headers).get('Idempotency-Key'),
    );
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBeTruthy();
    expect(keys[1]).toBe(keys[0]);
    expect(screen.getByRole('heading', { name: 'uploaded.png' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Tải lên và nhận dạng' })).toBeDisabled();
  });

  it('dùng khóa mới khi chọn file khác nội dung dù metadata giống nhau', async () => {
    const sendUpload = vi
      .fn<(options?: RequestInit) => Promise<Response>>()
      .mockRejectedValueOnce(new TypeError('Network offline'))
      .mockResolvedValueOnce(response(document('uploaded', 'succeeded')));
    mockWorkspace(sendUpload);
    const options = { type: 'image/png', lastModified: 123 };
    select(new File(['a'], 'sample.png', options));
    fireEvent.click(screen.getByRole('checkbox', { name: /Tôi xác nhận/ }));
    await send();

    select(new File(['b'], 'sample.png', options));
    await send();
    const keys = sendUpload.mock.calls.map(([requestOptions]) =>
      new Headers(requestOptions?.headers).get('Idempotency-Key'),
    );
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBeTruthy();
    expect(keys[1]).toBeTruthy();
    expect(keys[1]).not.toBe(keys[0]);
  });
});
