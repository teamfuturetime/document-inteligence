import { useState } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SessionBoundary } from './SessionBoundary';
import { getSessionSnapshot, refreshSession, sessionFetch } from '../../lib/session';
import { request } from '../documents/api';

const alpha = { id: 'a'.repeat(32), username: 'alpha' };
const beta = { id: 'b'.repeat(32), username: 'beta' };
const anonymous = { mode: 'session', user: null, csrf_token: null };
const local = { mode: 'local', user: null, csrf_token: null };
const authenticated = (user = alpha) => ({ mode: 'session', user, csrf_token: user.id + 'csrf' });
let state: ReturnType<typeof authenticated> | typeof anonymous | typeof local;
let calls: Array<{ path: string; options?: RequestInit }>;

function response(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}
function mockAPI() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options?: RequestInit) => {
      calls.push({ path, options });
      if (path.endsWith('/login')) {
        const credentials = JSON.parse(String(options?.body));
        if (credentials.password === 'wrong-password-123') {
          return response({ error: { message: 'Thông tin đăng nhập không hợp lệ.' } }, 401);
        }
        state = authenticated();
      }
      if (path.endsWith('/logout')) {
        state = anonymous;
        return response(null, 204);
      }
      return response(state);
    }),
  );
}
function renderBoundary(unsaved = false) {
  return render(
    <SessionBoundary unsaved={unsaved} onReset={vi.fn()}>
      <div>Tài liệu bí mật của phiên</div>
    </SessionBoundary>,
  );
}
beforeEach(async () => {
  state = anonymous;
  calls = [];
  mockAPI();
  await refreshSession();
});
afterEach(() => vi.unstubAllGlobals());

describe('Session boundary and account isolation', () => {
  it('ignores a canceled late session 401 and preserves the owner draft until verified', async () => {
    state = authenticated();
    await refreshSession();
    const key = `field-review:user:${alpha.id}:doc:run:editor`;
    localStorage.setItem(key, 'pending draft');
    let finish!: (value: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const controller = new AbortController();
    const pending = refreshSession(controller.signal);
    controller.abort();
    finish(response({ error: { code: 'AUTH_REQUIRED' } }, 401));
    await pending;
    expect(getSessionSnapshot().session?.user?.id).toBe(alpha.id);
    expect(localStorage.getItem(key)).toBe('pending draft');
    expect(getSessionSnapshot().uncertain).toBe(true);
    await refreshSession();
    expect(getSessionSnapshot().uncertain).toBe(false);
    localStorage.removeItem(key);
  });
  it('keeps identity/draft uncertain after a session timeout and rejects its late body', async () => {
    state = authenticated();
    await refreshSession();
    vi.useFakeTimers();
    const controller = new AbortController();
    const timeout = vi.spyOn(AbortSignal, 'timeout').mockReturnValue(controller.signal);
    let finish!: (value: unknown) => void;
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    } as Response);
    const pending = refreshSession();
    await act(async () => {});
    setTimeout(() => controller.abort(), 8000);
    await vi.advanceTimersByTimeAsync(8000);
    finish(authenticated(beta));
    await pending;
    expect(getSessionSnapshot().session?.user?.id).toBe(alpha.id);
    expect(getSessionSnapshot().uncertain).toBe(true);
    await expect(sessionFetch('/api/v1/documents')).rejects.toMatchObject({ name: 'AbortError' });
    timeout.mockRestore();
    vi.useRealTimers();
  });
  it('honors a verified protected 401 even after a concurrent session lookup failed', async () => {
    state = authenticated();
    await refreshSession();
    const key = `field-review:user:${alpha.id}:doc:run:editor`;
    localStorage.setItem(key, 'private draft');
    let finish!: (value: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const pending = sessionFetch('/api/v1/documents').catch((error) => error);
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('offline'));
    await refreshSession();
    expect(getSessionSnapshot().uncertain).toBe(true);
    finish(response({ error: { code: 'AUTH_REQUIRED' } }, 401));
    await pending;
    expect(getSessionSnapshot().session?.user).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
  });
  it('blocks protected requests while an identity recheck is still pending', async () => {
    state = authenticated();
    await refreshSession();
    let finish!: (value: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const pending = refreshSession();
    const before = vi.mocked(fetch).mock.calls.length;
    const protectedCall = sessionFetch('/api/v1/documents').catch((error) => error);
    expect(await protectedCall).toMatchObject({ name: 'AbortError' });
    expect(fetch).toHaveBeenCalledTimes(before);
    finish(response(authenticated(beta)));
    await pending;
    expect(getSessionSnapshot().session?.user?.id).toBe(beta.id);
  });
  it.each([200, 500])(
    'does not accept a protected %s body from before a same-owner revalidation',
    async (status) => {
      state = authenticated();
      await refreshSession();
      let finish!: (value: unknown) => void;
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: status === 200,
        status,
        json: () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      } as Response);
      const old = request('/documents').catch((error) => error);
      await waitFor(() => expect(finish).toBeDefined());
      await refreshSession();
      finish({ stale: 'private response' });
      expect(await old).toMatchObject({ name: 'AbortError' });
    },
  );
  it('keeps a known editor mounted while offline, blocks requests until verification, then resets on verified 401', async () => {
    state = authenticated();
    renderBoundary(true);
    await screen.findByText('Tài liệu bí mật của phiên');
    const original = screen.getByText('Tài liệu bí mật của phiên');
    const revision = getSessionSnapshot().revision;
    localStorage.setItem(`field-review:user:${alpha.id}:doc:run:editor`, 'private draft');
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('offline'));
    await act(async () => {
      await refreshSession();
    });
    expect(screen.getByText('Tài liệu bí mật của phiên')).toBe(original);
    expect(getSessionSnapshot().revision).toBe(revision);
    expect(getSessionSnapshot().uncertain).toBe(true);
    expect(screen.getByRole('status', { name: 'Xác minh phiên' })).toHaveTextContent(
      'Bản nháp vẫn được giữ',
    );
    const before = vi.mocked(fetch).mock.calls.length;
    await expect(sessionFetch('/api/v1/documents')).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetch).toHaveBeenCalledTimes(before);
    await act(async () => {
      await refreshSession();
    });
    expect(getSessionSnapshot().uncertain).toBe(false);
    expect(screen.getByText('Tài liệu bí mật của phiên')).toBe(original);
    vi.mocked(fetch).mockResolvedValueOnce(response({ error: { code: 'AUTH_REQUIRED' } }, 401));
    await act(async () => {
      await refreshSession();
    });
    expect(screen.getByRole('button', { name: 'Đăng nhập' })).toBeVisible();
    expect(localStorage.getItem(`field-review:user:${alpha.id}:doc:run:editor`)).toBeNull();
  });
  it('does not restore an authenticated observation completed after logout', async () => {
    state = authenticated();
    renderBoundary();
    await screen.findByText('Tài liệu bí mật của phiên');
    let finishLogout!: (value: Response) => void;
    let finishRefresh!: (value: Response) => void;
    const logoutResponse = new Promise<Response>((resolve) => {
      finishLogout = resolve;
    });
    const refreshResponse = new Promise<Response>((resolve) => {
      finishRefresh = resolve;
    });
    vi.mocked(fetch).mockImplementation(async (path) =>
      String(path).endsWith('/logout') ? logoutResponse : refreshResponse,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Đăng xuất' }));
    window.dispatchEvent(new Event('focus'));
    await act(async () => {
      finishLogout(response(null, 204));
    });
    await act(async () => {
      finishRefresh(response(authenticated()));
    });
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible();
    expect(screen.queryByText('Tài liệu bí mật của phiên')).not.toBeInTheDocument();
  });

  it('still rejects a pending login invalidated by a real cross-tab session change', async () => {
    let notify!: () => void;
    vi.stubGlobal(
      'BroadcastChannel',
      class {
        set onmessage(value: () => void) {
          notify = value;
        }
        postMessage() {}
        close() {}
      },
    );
    renderBoundary();
    await screen.findByRole('button', { name: 'Đăng nhập' });
    let finishLogin!: (value: Response) => void;
    const loginResponse = new Promise<Response>((resolve) => {
      finishLogin = resolve;
    });
    vi.mocked(fetch).mockImplementation(async (path) =>
      String(path).endsWith('/login') ? loginResponse : response(authenticated(beta)),
    );
    fireEvent.change(screen.getByLabelText('Tên đăng nhập'), { target: { value: 'alpha' } });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), {
      target: { value: 'synthetic-password-123' },
    });
    fireEvent.submit(screen.getByLabelText('Mật khẩu').closest('form')!);
    await act(async () => {
      notify();
    });
    expect(await screen.findByText('beta')).toBeVisible();
    await act(async () => {
      finishLogin(response(authenticated()));
    });
    expect(getSessionSnapshot().session?.user?.id).toBe(beta.id);
    expect(screen.queryByText('alpha')).not.toBeInTheDocument();
  });

  it.each(['before', 'after'])(
    'accepts successful login when focus refresh finishes %s the login response',
    async (timing) => {
      renderBoundary();
      await screen.findByRole('button', { name: 'Đăng nhập' });
      let finishLogin!: (value: Response) => void;
      let finishRefresh!: (value: Response) => void;
      const loginResponse = new Promise<Response>((resolve) => {
        finishLogin = resolve;
      });
      const refreshResponse = new Promise<Response>((resolve) => {
        finishRefresh = resolve;
      });
      vi.mocked(fetch).mockImplementation(async (path) =>
        String(path).endsWith('/login') ? loginResponse : refreshResponse,
      );
      fireEvent.change(screen.getByLabelText('Tên đăng nhập'), { target: { value: 'alpha' } });
      fireEvent.change(screen.getByLabelText('Mật khẩu'), {
        target: { value: 'synthetic-password-123' },
      });
      fireEvent.submit(screen.getByLabelText('Mật khẩu').closest('form')!);
      window.dispatchEvent(new Event('focus'));
      if (timing === 'before')
        await act(async () => {
          finishRefresh(response(anonymous));
        });
      await act(async () => {
        finishLogin(response(authenticated()));
      });
      if (timing === 'after')
        await act(async () => {
          finishRefresh(response(anonymous));
        });
      expect(await screen.findByText('alpha')).toBeVisible();
      expect(screen.getByText('Tài liệu bí mật của phiên')).toBeVisible();
      expect(screen.queryByRole('button', { name: 'Đăng nhập' })).not.toBeInTheDocument();
      expect(screen.queryByText('Phiên đã thay đổi. Hãy đăng nhập lại.')).not.toBeInTheDocument();
    },
  );

  it('gates documents, logs in without storing credentials and sends CSRF for logout', async () => {
    renderBoundary();
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible();
    expect(screen.queryByText('Tài liệu bí mật của phiên')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Tên đăng nhập'), { target: { value: 'alpha' } });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), {
      target: { value: 'synthetic-password-123' },
    });
    fireEvent.submit(screen.getByRole('button', { name: 'Đăng nhập' }).closest('form')!);
    expect(await screen.findByText('Tài liệu bí mật của phiên')).toBeVisible();
    expect(screen.getByText('alpha')).toBeVisible();
    const loginCall = calls.find((call) => call.path.endsWith('/login'))!;
    expect(new Headers(loginCall.options?.headers).get('X-Requested-With')).toBe('docintel');
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    fireEvent.click(screen.getByRole('button', { name: 'Đăng xuất' }));
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible();
    const logoutCall = calls.find((call) => call.path.endsWith('/logout'))!;
    expect(new Headers(logoutCall.options?.headers).get('X-CSRF-Token')).toBe(alpha.id + 'csrf');
    expect(screen.queryByText('Tài liệu bí mật của phiên')).not.toBeInTheDocument();
  });

  it('keeps rejected login generic, clears password and allows retry', async () => {
    renderBoundary();
    const password = await screen.findByLabelText('Mật khẩu');
    fireEvent.change(screen.getByLabelText('Tên đăng nhập'), { target: { value: 'alpha' } });
    fireEvent.change(password, { target: { value: 'wrong-password-123' } });
    fireEvent.submit(password.closest('form')!);
    expect(await screen.findByRole('alert')).toHaveTextContent('Thông tin đăng nhập không hợp lệ.');
    expect(password).toHaveValue('');
    expect(screen.queryByText('Tài liệu bí mật của phiên')).not.toBeInTheDocument();
  });

  it('clears documents immediately when a protected request receives 401', async () => {
    state = authenticated();
    renderBoundary();
    expect(await screen.findByText('Tài liệu bí mật của phiên')).toBeVisible();
    vi.mocked(fetch).mockResolvedValueOnce(response({ error: { code: 'AUTH_REQUIRED' } }, 401));
    await sessionFetch('/api/v1/documents');
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible();
    expect(screen.queryByText('Tài liệu bí mật của phiên')).not.toBeInTheDocument();
  });

  it('remounts the workspace on an account change and blocks old responses', async () => {
    state = authenticated();
    let mounts = 0;
    function WorkspaceProbe() {
      const [id] = useState(() => ++mounts);
      return <span>Workspace {id}</span>;
    }
    render(
      <SessionBoundary unsaved={false} onReset={vi.fn()}>
        <WorkspaceProbe />
      </SessionBoundary>,
    );
    expect(await screen.findByText('Workspace 1')).toBeVisible();
    let resolve!: (value: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(
      () =>
        new Promise<Response>((done) => {
          resolve = done;
        }),
    );
    const old = request('/documents').catch((error: Error) => error);
    state = authenticated(beta);
    window.dispatchEvent(new Event('focus'));
    expect(await screen.findByText('beta')).toBeVisible();
    expect(screen.getByText('Workspace 2')).toBeVisible();
    resolve(response({ private: 'alpha' }));
    expect(await old).toMatchObject({ name: 'AbortError' });
  });

  it('blocks a response body completed after an identity change', async () => {
    state = authenticated();
    await refreshSession();
    let resolve!: (value: unknown) => void;
    const body = new Promise((done) => {
      resolve = done;
    });
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, status: 200, json: () => body } as Response);
    const old = request('/documents').catch((error: Error) => error);
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    state = authenticated(beta);
    await refreshSession();
    resolve({ private: 'alpha' });
    expect(await old).toMatchObject({ name: 'AbortError' });
  });

  it('keeps the workspace closed when session lookup fails', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('offline'));
    renderBoundary();
    expect(await screen.findByRole('alert')).toHaveTextContent('Không kiểm tra được phiên');
    expect(screen.queryByText('Tài liệu bí mật của phiên')).not.toBeInTheDocument();
    expect(getSessionSnapshot().session).toBeNull();
  });

  it('keeps local mode working without login and prevents logout with unsaved edits', async () => {
    state = local;
    const view = renderBoundary();
    expect(await screen.findByText('Tài liệu bí mật của phiên')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Đăng nhập' })).not.toBeInTheDocument();
    view.unmount();
    state = authenticated();
    renderBoundary(true);
    expect(await screen.findByRole('button', { name: 'Đăng xuất' })).toBeDisabled();
    expect(screen.getByText(/Hãy lưu hoặc bỏ chỉnh sửa/)).toBeVisible();
  });
});
