import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ready from '../../../contracts/examples/readiness-ready.json';
import notReady from '../../../contracts/examples/readiness-not-ready.json';
import { App } from '../app/App';
import { readReadiness, useLiveReadiness } from './readiness';
import { refreshSession } from './session';

const capabilities = {
  ocr_ready: true,
  provider_mode: 'tesseract',
  max_upload_bytes: 5242880,
  features: {},
  supported_schemas: [],
  model_benchmark_status: 'not_measured',
};
const local = { mode: 'local', user: null, csrf_token: null };
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const count = (suffix: string) =>
  vi.mocked(fetch).mock.calls.filter(([path]) => String(path).endsWith(suffix)).length;
async function advance(ms = 0) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

beforeEach(async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => response(local)),
  );
  await refreshSession();
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function api() {
  const readiness = vi.fn<(signal?: AbortSignal | null) => Promise<Response>>(async () =>
    response(ready),
  );
  const capability = vi.fn(async () => response(capabilities));
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options?: RequestInit) => {
      if (path.endsWith('/readiness')) return readiness(options?.signal);
      if (path.endsWith('/auth/session')) return response(local);
      if (path.endsWith('/capabilities')) return capability();
      if (path.endsWith('/document-schemas')) return response([]);
      if (path.includes('/documents?'))
        return response({ items: [], total: 0, limit: 10, offset: 0 });
      if (path.endsWith('/insights')) return response({ documents: 0 });
      throw new Error(`Unexpected ${path}`);
    }),
  );
  return { readiness, capability };
}

describe('Live readiness lifecycle', () => {
  it('parses 200/503 using the generated model and rejects mismatched/malformed bodies', async () => {
    for (const [body, status, valid] of [
      [ready, 200, true],
      [notReady, 503, true],
      [ready, 503, false],
      [{ status: 'ready' }, 200, false],
      [{ error: { message: 'Unavailable' } }, 503, false],
      [{ ...ready, worker: 'invented' }, 200, false],
    ] as const) {
      vi.stubGlobal(
        'fetch',
        vi.fn(async () => response(body, status)),
      );
      const result = readReadiness(new AbortController().signal);
      if (valid) await expect(result).resolves.toEqual(body);
      else await expect(result).rejects.toThrow();
    }
  });
  it('polls healthy readiness without repeatedly probing capabilities', async () => {
    api();
    const view = renderHook(useLiveReadiness);
    await advance();
    expect(view.result.current.status).toBe('ready');
    await advance(45000);
    expect(count('/readiness')).toBe(4);
    expect(count('/capabilities')).toBe(1);
    expect(count('/auth/session')).toBe(1);
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
  it('bounds backoff and manual retry storms, and never replays a write', async () => {
    const { readiness } = api();
    readiness.mockRejectedValue(new TypeError('offline'));
    const view = renderHook(useLiveReadiness);
    await advance(61000);
    expect(count('/readiness')).toBe(7);
    expect(view.result.current.status).toBe('reconnecting');
    for (let i = 0; i < 50; i++) view.result.current.retry();
    await advance(999);
    expect(count('/readiness')).toBe(7);
    await advance(1);
    expect(count('/readiness')).toBe(8);
    expect(count('/capabilities')).toBe(0);
    expect(
      vi
        .mocked(fetch)
        .mock.calls.every(([, options]) => !options?.method || options.method === 'GET'),
    ).toBe(true);
  });
  it('keeps upload disabled on 503 and refreshes capabilities only on recovery', async () => {
    const { readiness, capability } = api();
    readiness.mockResolvedValueOnce(response(notReady, 503));
    render(<App />);
    await advance();
    fireEvent.click(screen.getByRole('button', { name: 'Xử lý tài liệu' }));
    await advance();
    fireEvent.change(screen.getByLabelText('Ảnh PNG/JPG một trang'), {
      target: { files: [new File(['sample'], 'sample.png', { type: 'image/png' })] },
    });
    fireEvent.click(screen.getByRole('checkbox', { name: /Tôi xác nhận/ }));
    expect(screen.getByRole('status', { name: 'Trạng thái backend' })).toHaveTextContent(
      'Chưa sẵn sàng',
    );
    expect(screen.getByRole('button', { name: 'Tải lên và nhận dạng' })).toBeDisabled();
    expect(capability).toHaveBeenCalledTimes(1);
    await advance(1000);
    expect(screen.getByRole('button', { name: 'Tải lên và nhận dạng' })).toBeEnabled();
    expect(capability).toHaveBeenCalledTimes(2);
    expect(screen.getByRole('status', { name: 'Trạng thái backend' })).toHaveAttribute(
      'aria-atomic',
      'true',
    );
    await advance(15000);
    expect(capability).toHaveBeenCalledTimes(2);
  });
  it('cancels pending requests, ignores late bodies and pauses while hidden without a wake storm', async () => {
    const { readiness } = api();
    let hidden = false;
    vi.spyOn(document, 'hidden', 'get').mockImplementation(() => hidden);
    let finish!: (value: Response) => void;
    readiness.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const view = renderHook(useLiveReadiness);
    await advance();
    const signal = readiness.mock.calls[0][0];
    hidden = true;
    act(() => document.dispatchEvent(new Event('visibilitychange')));
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      finish(response(ready));
    });
    await advance(120000);
    expect(count('/readiness')).toBe(1);
    hidden = false;
    for (let i = 0; i < 30; i++)
      act(() => {
        document.dispatchEvent(new Event('visibilitychange'));
        window.dispatchEvent(new Event('online'));
      });
    await advance(1000);
    expect(count('/readiness')).toBe(2);
    expect(view.result.current.status).toBe('ready');
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
  it('times out an unresponsive request before retrying, with no overlap', async () => {
    const { readiness } = api();
    readiness.mockImplementationOnce(
      (signal) =>
        new Promise((_resolve, reject) =>
          signal?.addEventListener('abort', () =>
            reject(new DOMException('timeout', 'AbortError')),
          ),
        ),
    );
    renderHook(useLiveReadiness);
    await advance(7999);
    expect(readiness).toHaveBeenCalledTimes(1);
    await advance(1001);
    expect(readiness).toHaveBeenCalledTimes(2);
  });
  it('ignores capabilities completed after account change', async () => {
    const { capability } = api();
    let finish!: (value: unknown) => void;
    capability.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    } as Response);
    const view = renderHook(useLiveReadiness);
    await advance();
    vi.mocked(fetch).mockImplementationOnce(async () =>
      response({
        mode: 'session',
        user: { id: 'b'.repeat(32), username: 'beta' },
        csrf_token: 'beta-csrf',
      }),
    );
    await act(async () => {
      await refreshSession();
    });
    await act(async () => {
      finish({ ...capabilities, max_upload_bytes: 1 });
    });
    expect(view.result.current.capabilities?.max_upload_bytes).not.toBe(1);
    expect(view.result.current.status).toBe('reconnecting');
  });
});
