import { useEffect, useState, useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';
import {
  getSessionSnapshot,
  login,
  logout,
  refreshSession,
  subscribeSession,
  watchSession,
} from '../../lib/session';

export function SessionBoundary({
  children,
  unsaved,
  onReset,
}: {
  children: ReactNode;
  unsaved: boolean;
  onReset: () => void;
}) {
  const { session, error, revision } = useSyncExternalStore(subscribeSession, getSessionSnapshot);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let active = true;
    void refreshSession().finally(() => {
      if (active) setReady(true);
    });
    const stop = watchSession();
    return () => {
      active = false;
      stop();
    };
  }, []);
  useEffect(() => {
    onReset();
    setPassword('');
    setActionError('');
  }, [revision, onReset]);

  if (!ready || !session) {
    return (
      <section className="section" aria-label="Phiên đăng nhập">
        {error ? (
          <>
            <p role="alert">{error}</p>
            <button onClick={() => void refreshSession()}>Thử lại phiên</button>
          </>
        ) : (
          <p role="status">Đang kiểm tra phiên…</p>
        )}
      </section>
    );
  }
  if (session.mode === 'session' && !session.user) {
    return (
      <section className="section auth-panel" aria-label="Đăng nhập">
        <h1>Đăng nhập để xử lý tài liệu</h1>
        <p>
          Mỗi tài khoản chỉ truy cập tài liệu của mình. Liên hệ người quản lý để được cấp tài khoản.
        </p>
        {(error || actionError) && <p role="alert">{actionError || error}</p>}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setBusy(true);
            setActionError('');
            void login(username, password)
              .catch((reason: Error) => setActionError(reason.message))
              .finally(() => {
                setPassword('');
                setBusy(false);
              });
          }}
        >
          <label>
            Tên đăng nhập
            <input
              name="username"
              autoComplete="username"
              required
              pattern="[a-z][a-z0-9_-]{2,31}"
              maxLength={32}
              value={username}
              disabled={busy}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label>
            Mật khẩu
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              minLength={12}
              maxLength={128}
              value={password}
              disabled={busy}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <button className="primary" disabled={busy} type="submit">
            {busy ? 'Đang đăng nhập…' : 'Đăng nhập'}
          </button>
        </form>
      </section>
    );
  }
  return (
    <div key={revision}>
      {session.mode === 'session' && session.user && (
        <section className="session-bar" aria-label="Tài khoản hiện tại">
          <span>
            Đang đăng nhập: <strong>{session.user.username}</strong>
          </span>
          <button
            disabled={busy || unsaved}
            onClick={() => {
              setBusy(true);
              setActionError('');
              void logout()
                .catch((reason: Error) => setActionError(reason.message))
                .finally(() => setBusy(false));
            }}
          >
            Đăng xuất
          </button>
          {unsaved && <span>Hãy lưu hoặc bỏ chỉnh sửa trước khi đăng xuất.</span>}
          {actionError && <p role="alert">{actionError}</p>}
        </section>
      )}
      {children}
    </div>
  );
}
