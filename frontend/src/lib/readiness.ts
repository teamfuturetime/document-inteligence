import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import schema from '../../../contracts/generated/Readiness.schema.json';
import type { components } from './api.generated';
import type { Capabilities } from './api';
import { request } from '../features/documents/api';
import { getSessionSnapshot, refreshSession, subscribeSession } from './session';

export type Readiness = components['schemas']['Readiness'];
type Connection = {
  status: 'ready' | 'not_ready' | 'reconnecting';
  readiness: Readiness | null;
  capabilities: Capabilities | null;
  recovery: number;
  revision: number;
};

export async function readReadiness(signal: AbortSignal): Promise<Readiness> {
  const response = await fetch('/api/v1/readiness', {
    signal,
    credentials: 'same-origin',
    cache: 'no-store',
  });
  // Readiness 503 is a domain response, never an ErrorEnvelope.
  if (response.status !== 200 && response.status !== 503) throw new Error('Readiness unavailable');
  const value: unknown = await response.json();
  signal.throwIfAborted();
  if (!value || typeof value !== 'object') throw new Error('Invalid readiness');
  const fields = value as Record<string, unknown>;
  for (const key of schema.required) if (!(key in fields)) throw new Error('Invalid readiness');
  for (const [key, field] of Object.entries(schema.properties)) {
    if (!(key in fields)) continue;
    if (
      typeof fields[key] !== 'string' ||
      ('enum' in field && !field.enum.includes(fields[key] as never)) ||
      ('const' in field && fields[key] !== field.const)
    )
      throw new Error('Invalid readiness');
  }
  if (fields.status !== (response.status === 200 ? 'ready' : 'not_ready'))
    throw new Error('Invalid readiness status');
  return value as Readiness;
}

export function useLiveReadiness() {
  const session = useSyncExternalStore(subscribeSession, getSessionSnapshot);
  const [connection, setConnection] = useState<Connection>({
    status: 'reconnecting',
    readiness: null,
    capabilities: null,
    recovery: 0,
    revision: -1,
  });
  const retryRef = useRef<() => void>(() => {});
  const retry = useCallback(() => retryRef.current(), []);
  useEffect(() => {
    const revision = session.revision;
    let disposed = false;
    let generation = 0;
    let timer: number | undefined;
    let controller: AbortController | undefined;
    let requestTimeout: number | undefined;
    let failures = 0;
    let nextDelay = 1000;
    let lastStarted = -Infinity;
    let wasReady = false;
    let refreshCapabilities = true;
    let capabilities: Capabilities | null = null;
    const pause = () => {
      ++generation;
      window.clearTimeout(timer);
      window.clearTimeout(requestTimeout);
      timer = undefined;
      controller?.abort();
      controller = undefined;
    };
    const schedule = (delay: number) => {
      if (disposed || document.hidden || timer !== undefined || controller) return;
      timer = window.setTimeout(() => {
        timer = undefined;
        void poll();
      }, delay);
    };
    const poll = async () => {
      const attempt = ++generation;
      const pending = new AbortController();
      controller = pending;
      lastStarted = Date.now();
      const timeout = window.setTimeout(() => pending.abort(), 8000);
      requestTimeout = timeout;
      const current = () =>
        !disposed &&
        attempt === generation &&
        !pending.signal.aborted &&
        getSessionSnapshot().revision === revision;
      try {
        const readiness = await readReadiness(pending.signal);
        if (!current()) return;
        const reload =
          refreshCapabilities ||
          (!wasReady && readiness.status === 'ready') ||
          getSessionSnapshot().uncertain;
        if (reload) {
          if (!(await refreshSession(pending.signal))) throw new Error('Session unavailable');
          if (!current()) return;
          capabilities = await request<Capabilities>('/capabilities', {
            signal: pending.signal,
            cache: 'no-store',
          });
        }
        if (!current()) return;
        refreshCapabilities = false;
        wasReady = readiness.status === 'ready';
        setConnection((old) => ({
          status: readiness.status,
          readiness,
          capabilities,
          revision,
          recovery: old.recovery + Number(reload),
        }));
        if (wasReady) {
          failures = 0;
          nextDelay = 15000;
        } else nextDelay = Math.min(1000 * 2 ** Math.min(failures++, 5), 30000);
      } catch {
        if (disposed || attempt !== generation) return;
        wasReady = false;
        refreshCapabilities = true;
        setConnection((old) => ({ ...old, status: 'reconnecting', revision }));
        nextDelay = Math.min(1000 * 2 ** Math.min(failures++, 5), 30000);
      } finally {
        window.clearTimeout(timeout);
        if (!disposed && attempt === generation) {
          controller = undefined;
          schedule(nextDelay);
        }
      }
    };
    const visibility = () => {
      if (document.hidden) {
        pause();
        wasReady = false;
        refreshCapabilities = true;
        setConnection((old) => ({ ...old, status: 'reconnecting' }));
      } else schedule(Math.max(1000, nextDelay));
    };
    const online = () => schedule(Math.max(1000, nextDelay));
    retryRef.current = () => {
      if (controller || document.hidden) return;
      window.clearTimeout(timer);
      timer = undefined;
      schedule(Math.max(0, 1000 - (Date.now() - lastStarted)));
    };
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('online', online);
    schedule(0);
    return () => {
      disposed = true;
      pause();
      retryRef.current = () => {};
      document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener('online', online);
    };
  }, [session.revision]);
  return {
    ...connection,
    status:
      connection.revision !== session.revision || session.uncertain
        ? ('reconnecting' as const)
        : connection.status,
    retry,
  };
}
