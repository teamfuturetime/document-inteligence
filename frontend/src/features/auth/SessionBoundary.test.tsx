import { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
