import type { components } from './api.generated';
import { clearReviewDrafts } from './reviewDrafts';

export type SessionState = components['schemas']['SessionState'];
type Snapshot = { session: SessionState | null; error: string; revision: number };
let snapshot: Snapshot = { session: null, error: '', revision: 0 };
let refreshSequence = 0;
let mutationSequence = 0;
let pendingMutation: number | null = null;
let draftIdentity: string | null = null;
const listeners = new Set<() => void>();
let channel: BroadcastChannel | undefined;

export const getSessionSnapshot = () => snapshot;
export function subscribeSession(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function publish(session: SessionState | null, error = '') {
  // A failed lookup is unknown, not proof of logout. Keep only namespaced recovery
  // until a verified anonymous/different identity or cross-tab invalidation arrives.
  if (session) {
    const nextIdentity = session.mode === 'local' ? 'local' : (session.user?.id ?? null);
    if (draftIdentity && draftIdentity !== nextIdentity) clearReviewDrafts(draftIdentity);
    draftIdentity = nextIdentity;
  }
  const previous = snapshot.session;
  const changed =
    previous?.mode !== session?.mode ||
    previous?.user?.id !== session?.user?.id ||
    previous?.csrf_token !== session?.csrf_token;
  snapshot = { session, error, revision: snapshot.revision + Number(changed) };
  listeners.forEach((listener) => listener());
}

async function sessionResponse(response: Response): Promise<SessionState> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.error?.message ?? 'Không kiểm tra được phiên đăng nhập.');
  }
  return response.json() as Promise<SessionState>;
}

export async function refreshSession() {
  const sequence = ++refreshSequence;
  const mutation = mutationSequence;
  const isCurrent = () =>
    sequence === refreshSequence && mutation === mutationSequence && pendingMutation === null;
  try {
    const state = await sessionResponse(
      await fetch('/api/v1/auth/session', { credentials: 'same-origin', cache: 'no-store' }),
    );
    if (isCurrent()) publish(state);
  } catch {
    if (isCurrent()) publish(null, 'Không kiểm tra được phiên. Hãy thử lại.');
  }
}

function invalidateSessionRequests() {
  ++refreshSequence;
  ++mutationSequence;
  pendingMutation = null;
}

function beginMutation() {
  ++refreshSequence;
  pendingMutation = ++mutationSequence;
  return pendingMutation;
}

function finishMutation(sequence: number) {
  if (sequence !== mutationSequence) return;
  pendingMutation = null;
  // Discard observations started during the mutation, even if their bodies arrive later.
  ++refreshSequence;
}

function notifyOtherTabs() {
  channel?.postMessage('session-changed'); // No identity, credentials or document data in storage.
}

export function watchSession() {
  const refresh = () => void refreshSession();
  const visible = () => {
    if (document.visibilityState === 'visible') refresh();
  };
  window.addEventListener('focus', refresh);
  window.addEventListener('pageshow', refresh);
  document.addEventListener('visibilitychange', visible);
  if (typeof BroadcastChannel !== 'undefined') {
    channel = new BroadcastChannel('docintel-session');
    channel.onmessage = () => {
      invalidateSessionRequests();
      if (draftIdentity) clearReviewDrafts(draftIdentity);
      draftIdentity = null;
      publish(null);
      refresh();
    };
  }
  return () => {
    window.removeEventListener('focus', refresh);
    window.removeEventListener('pageshow', refresh);
    document.removeEventListener('visibilitychange', visible);
    channel?.close();
    channel = undefined;
  };
}

export async function login(username: string, password: string) {
  const sequence = beginMutation();
  try {
    const state = await sessionResponse(
      await fetch('/api/v1/auth/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'docintel' },
        body: JSON.stringify({ username, password }),
      }),
    );
    if (sequence !== mutationSequence) throw new Error('Phiên đã thay đổi. Hãy đăng nhập lại.');
    publish(state);
    notifyOtherTabs();
  } finally {
    finishMutation(sequence);
  }
}

export function assertCurrentSession(revision: number) {
  if (revision !== snapshot.revision) {
    throw new DOMException('Phiên đã thay đổi; thao tác cũ đã dừng.', 'AbortError');
  }
}

export async function sessionFetch(path: string, options: RequestInit = {}) {
  const revision = snapshot.revision;
  const headers = new Headers(options.headers);
  const method = (options.method ?? 'GET').toUpperCase();
  const csrf = snapshot.session?.csrf_token;
  if (csrf && !['GET', 'HEAD', 'OPTIONS'].includes(method)) headers.set('X-CSRF-Token', csrf);
  const response = await fetch(path, { ...options, headers, credentials: 'same-origin' });
  assertCurrentSession(revision);
  if (response.status === 401) {
    invalidateSessionRequests();
    publish(
      { mode: 'session', user: null, csrf_token: null },
      'Phiên đã hết hạn. Vui lòng đăng nhập lại.',
    );
    notifyOtherTabs();
  } else if (response.status === 403 && snapshot.session?.mode === 'session') {
    // A cookie may have changed in another tab. Never replay the failed write.
    void refreshSession();
  }
  return response;
}

export async function logout() {
  const sequence = beginMutation();
  try {
    const response = await sessionFetch('/api/v1/auth/logout', { method: 'POST' });
    if (!response.ok) throw new Error('Chưa đăng xuất được. Hãy thử lại.');
    if (sequence !== mutationSequence) throw new Error('Phiên đã thay đổi. Hãy kiểm tra lại.');
    publish({ mode: 'session', user: null, csrf_token: null });
    notifyOtherTabs();
  } finally {
    finishMutation(sequence);
  }
}
