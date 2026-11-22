import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { logout, refreshSession, sessionFetch } from '../../lib/session';
import { SessionBoundary } from '../auth/SessionBoundary';
import { ReviewPanel } from './ReviewPanel';
import { SourcePreview } from './SourcePreview';
import type { DocumentDetail } from './api';

function document(revision = 1): DocumentDetail {
  return {
    document_id: 'doc',
    document_type: 'hoa_don',
    filename: 'sample.png',
    data_origin: 'synthetic',
    input_sha256: 'a'.repeat(64),
    image_width: 100,
    image_height: 100,
    created_at: '2026-10-24T00:00:00Z',
    latest_run_id: 'run',
    status: 'succeeded',
    image_url: '/source',
    is_latest_run: true,
    definitions: [
      { field_id: 'seller_name', label: 'Đơn vị bán hàng', value_type: 'text', required: true },
    ],
    run: {
      run_id: 'run',
      status: 'succeeded',
      created_at: '2026-10-24T00:00:00Z',
      fields: [
        {
          field_id: 'seller_name',
          raw_value: 'Công ty Mẫu',
          normalized_value: 'Công ty Mẫu',
          observation: 'found',
          evidence_span_ids: [],
          confidence: {
            method: 'heuristic',
            policy_version: 'unit-test-explicit',
            score: 0.8,
            ocr_score: 0.8,
          },
        },
      ],
      spans: [],
    },
    review: {
      revision,
      review_status: 'draft',
      saved_at: '2026-10-24T00:00:00Z',
      fields: { seller_name: { is_reviewed: false, reviewed_value: null } },
      effective_data: { seller_name: 'Công ty Mẫu' },
      validation_issues: [],
    },
  };
}

describe('Keyboard focus and announcements', () => {
  it('describes evidence and returns preview focus after image retry', () => {
    render(<SourcePreview document={document()} active="seller_name" />);
    expect(
      screen.getByRole('img', { name: 'Bằng chứng OCR: Đơn vị bán hàng' }),
    ).toHaveAccessibleDescription(/chưa có bằng chứng/);
    fireEvent.error(screen.getByRole('img', { name: 'Ảnh nguồn sample.png' }));
    fireEvent.click(screen.getByRole('button', { name: 'Thử tải lại ảnh' }));
    expect(screen.getByRole('region', { name: 'Đối chiếu ảnh nguồn' })).toHaveFocus();
  });
  it('focuses manual save error and returns to editor after explicit retry', async () => {
    const mock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: { code: 'FAIL', message: 'Failed' } }), {
          status: 500,
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(document(2))));
    vi.stubGlobal('fetch', mock);
    mountReview();
    fireEvent.change(screen.getByLabelText('Đơn vị bán hàng *'), { target: { value: 'Keep me' } });
    const save = screen.getByRole('button', { name: 'Lưu nháp' });
    save.focus();
    fireEvent.click(save);
    await waitFor(() =>
      expect(screen.getByRole('alert', { name: 'Lỗi lưu bản rà soát' })).toHaveFocus(),
    );
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Keep me');
    fireEvent.click(save);
    await waitFor(() => expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveFocus());
    expect(mock).toHaveBeenCalledTimes(2);
  });
  function mountReview() {
    return render(
      <ReviewPanel
        document={document()}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
  }
  it('does not restore stale focus when the user moves during a manual save', async () => {
    vi.useFakeTimers();
    let finishSave!: (value: Response) => void;
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>((resolve) => (finishSave = resolve))),
    );
    mountReview();
    const input = screen.getByLabelText('Đơn vị bán hàng *');
    fireEvent.change(input, { target: { value: 'Keep me' } });
    const save = screen.getByRole('button', { name: 'Lưu nháp' });
    save.focus();
    fireEvent.click(save);
    const next = screen.getByRole('button', { name: 'Xem vùng nguồn: Đơn vị bán hàng' });
    next.focus();
    // The later edit must survive the older ACK as well as keep the user's focus.
    fireEvent.change(input, { target: { value: 'Newer draft' } });
    await act(async () => {
      finishSave(new Response(JSON.stringify(document(2))));
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(next).toHaveFocus();
    expect(input).toHaveValue('Newer draft');
    expect(Object.values(localStorage).some((raw) => raw.includes('Newer draft'))).toBe(true);
  });
  it.each([false, true])(
    'focuses export after confirm only while focus remains in place (%s)',
    async (moveFocus) => {
      let finishConfirm!: (value: Response) => void;
      vi.stubGlobal(
        'fetch',
        vi.fn(() => new Promise<Response>((resolve) => (finishConfirm = resolve))),
      );
      const onUpdated = (next: DocumentDetail) => view.rerender(renderReview(next));
      const renderReview = (detail: DocumentDetail) => (
        <>
          <button type="button">Điểm đến khác</button>
          <ReviewPanel
            document={detail}
            onUpdated={onUpdated}
            onDirtyChange={vi.fn()}
            onFieldChange={vi.fn()}
          />
        </>
      );
      const view = render(renderReview(document()));
      const confirmButton = screen.getByRole('button', { name: 'Xác nhận bản lưu' });
      const other = screen.getByRole('button', { name: 'Điểm đến khác' });
      act(() => confirmButton.focus());
      fireEvent.click(confirmButton);
      if (moveFocus) act(() => other.focus());
      const confirmed = document(2);
      confirmed.review!.review_status = 'confirmed';
      await act(async () => finishConfirm(new Response(JSON.stringify(confirmed))));
      const exportButton = screen.getByRole('button', { name: 'Xuất JSON đã xác nhận' });
      await waitFor(() => expect(exportButton).toBeEnabled());
      expect(moveFocus ? other : exportButton).toHaveFocus();
    },
  );

  it('does not override a rapid focus move after discard', async () => {
    vi.useFakeTimers();
    mountReview();
    fireEvent.change(screen.getByLabelText('Đơn vị bán hàng *'), {
      target: { value: 'Discard me' },
    });
    const discard = screen.getByRole('button', { name: 'Bỏ chỉnh sửa' });
    discard.focus();
    fireEvent.click(discard);
    const next = screen.getByRole('button', { name: 'Xem vùng nguồn: Đơn vị bán hàng' });
    next.focus();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(next).toHaveFocus();
  });
  it('does not focus after discard and unmount', async () => {
    vi.useFakeTimers();
    const view = mountReview();
    fireEvent.change(screen.getByLabelText('Đơn vị bán hàng *'), {
      target: { value: 'Discard me' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Bỏ chỉnh sửa' }));
    view.unmount();
    render(<input aria-label="Next screen" />);
    const next = screen.getByLabelText('Next screen');
    next.focus();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(next).toHaveFocus();
  });
  it.each(['document', 'run'])('ignores a manual save ACK after switching %s', async (switchBy) => {
    vi.useFakeTimers();
    let finishSave!: (value: Response) => void;
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>((resolve) => (finishSave = resolve))),
    );
    const updated = vi.fn();
    function editor(value: DocumentDetail) {
      return (
        <StrictMode>
          <ReviewPanel
            key={`${value.document_id}-${value.run.run_id}`}
            document={value}
            onUpdated={updated}
            onDirtyChange={vi.fn()}
            onFieldChange={vi.fn()}
          />
        </StrictMode>
      );
    }
    const view = render(editor(document()));
    fireEvent.change(screen.getByLabelText('Đơn vị bán hàng *'), {
      target: { value: 'Previous document draft' },
    });
    const save = screen.getByRole('button', { name: 'Lưu nháp' });
    save.focus();
    fireEvent.click(save);
    const nextDocument = document();
    if (switchBy === 'document') nextDocument.document_id = 'next-doc';
    else nextDocument.run.run_id = nextDocument.latest_run_id = 'next-run';
    view.rerender(editor(nextDocument));
    const next = screen.getByRole('button', { name: 'Xem vùng nguồn: Đơn vị bán hàng' });
    next.focus();
    await act(async () => {
      finishSave(new Response(JSON.stringify(document(2))));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(next).toHaveFocus();
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Công ty Mẫu');
    expect(updated).not.toHaveBeenCalled();
    expect(Object.values(localStorage).some((raw) => raw.includes('Previous document draft'))).toBe(
      true,
    );
    expect(vi.getTimerCount()).toBe(0);
  });
  it('focuses the review heading, names status, and does not repeat announcements per keystroke', () => {
    mountReview();
    expect(screen.getByRole('heading', { name: 'Kiểm tra dữ liệu' })).toHaveFocus();
    const status = screen.getByRole('status', { name: 'Trạng thái lưu' });
    expect(status).toHaveAttribute('aria-atomic', 'true');
    const input = screen.getByLabelText('Đơn vị bán hàng *');
    input.focus();
    fireEvent.change(input, { target: { value: 'A' } });
    const first = status.textContent;
    fireEvent.change(input, { target: { value: 'AB' } });
    expect(status.textContent).toBe(first);
    expect(input).toHaveFocus();
  });
  it('focuses recovered draft error, compare region and then editor after discard, preserving foreign draft ownership', async () => {
    const key = 'field-review:doc:run:another-editor';
    const raw = JSON.stringify({
      at: Date.now(),
      fields: { seller_name: { is_reviewed: true, reviewed_value: null } },
    });
    localStorage.setItem(key, raw);
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify(document(2)))),
    );
    mountReview();
    expect(screen.getByRole('alert', { name: 'Lỗi lưu bản rà soát' })).toHaveFocus();
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('');
    fireEvent.click(screen.getByRole('button', { name: 'Đối chiếu bản mới' }));
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Đối chiếu chỉnh sửa với máy chủ' })).toHaveFocus(),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Bỏ chỉnh sửa, tải bản máy chủ' }));
    await waitFor(() => expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveFocus());
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Công ty Mẫu');
    expect(localStorage.getItem(key)).toBe(raw);
  });
  it('does not steal editor focus on background save errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ error: { code: 'FAIL', message: 'Failed' } }), {
            status: 500,
          }),
      ),
    );
    mountReview();
    const input = screen.getByLabelText('Đơn vị bán hàng *');
    input.focus();
    fireEvent.change(input, { target: { value: 'Keep edits' } });
    await screen.findByRole('alert', { name: 'Lỗi lưu bản rà soát' });
    expect(input).toHaveFocus();
    expect(input).toHaveValue('Keep edits');
    fireEvent.click(screen.getByRole('button', { name: /^Bỏ chỉnh sửa$/ }));
    await waitFor(() => expect(input).toHaveFocus());
  });
});

beforeEach(async () => {
  // These standalone autosave cases exercise local mode, as the app boundary would establish.
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      ok: true,
      json: async () => ({ mode: 'local', user: null, csrf_token: null }),
    })),
  );
  await refreshSession();
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  sessionStorage.clear();
  localStorage.clear();
});

describe('Authenticated draft recovery', () => {
  const alpha = { id: 'a'.repeat(32), username: 'alpha' };
  const beta = { id: 'b'.repeat(32), username: 'beta' };
  const ownerPrefix = (id: string) => `field-review:user:${id}:doc:run:`;
  const rawDraft = (value: string) =>
    JSON.stringify({
      at: Date.now(),
      fields: { seller_name: { is_reviewed: true, reviewed_value: value } },
    });
  function mountSession() {
    return render(
      <SessionBoundary unsaved={false} onReset={vi.fn()}>
        <ReviewPanel
          document={document()}
          onUpdated={vi.fn()}
          onDirtyChange={vi.fn()}
          onFieldChange={vi.fn()}
        />
      </SessionBoundary>,
    );
  }
  function server() {
    let user: typeof alpha | null = alpha;
    const fetchMock = vi.fn(async (path: string) => {
      if (path.endsWith('/logout')) {
        user = null;
        return { ok: true, status: 204 } as Response;
      }
      return {
        ok: true,
        status: 200,
        json: async () =>
          path.endsWith('/auth/session')
            ? { mode: 'session', user, csrf_token: user ? user.id + 'csrf' : null }
            : document(),
      } as Response;
    });
    vi.stubGlobal('fetch', fetchMock);
    return {
      fetchMock,
      setUser: (next: typeof alpha) => {
        user = next;
      },
    };
  }

  it('recovers only the current owner, excluding legacy and another account with the same resource IDs', async () => {
    const api = server();
    localStorage.setItem('field-review:doc:run:legacy', rawDraft('Unattributed legacy'));
    localStorage.setItem(ownerPrefix(alpha.id) + 'alpha-tab', rawDraft('Alpha private draft'));
    localStorage.setItem(ownerPrefix(beta.id) + 'beta-tab', rawDraft('Beta private draft'));
    mountSession();
    expect(await screen.findByLabelText('Đơn vị bán hàng *')).toHaveValue('Alpha private draft');
    expect(screen.getByRole('alert')).toHaveTextContent('RECOVERED_DRAFT');
    expect(api.fetchMock.mock.calls.filter(([path]) => path.endsWith('/review'))).toHaveLength(0);
  });

  it('namespaces changed fields and recovers the same account after a remount', async () => {
    server();
    const view = mountSession();
    fireEvent.change(await screen.findByLabelText('Đơn vị bán hàng *'), {
      target: { value: 'Alpha pending' },
    });
    const keys = Object.keys(localStorage).filter((key) => key.startsWith('field-review:'));
    expect(keys).toHaveLength(1);
    expect(keys[0]).toMatch(new RegExp('^' + ownerPrefix(alpha.id)));
    view.unmount();
    mountSession();
    expect(await screen.findByLabelText('Đơn vị bán hàng *')).toHaveValue('Alpha pending');
    expect(screen.getByRole('alert')).toHaveTextContent('RECOVERED_DRAFT');
  });

  it.each(['logout', 'expiry', 'account-change'])(
    'clears only the previous account draft on %s',
    async (change) => {
      const api = server();
      const alphaKey = ownerPrefix(alpha.id) + 'alpha-tab';
      const betaKey = ownerPrefix(beta.id) + 'beta-tab';
      localStorage.setItem(alphaKey, rawDraft('Alpha private draft'));
      localStorage.setItem(betaKey, rawDraft('Beta private draft'));
      mountSession();
      await screen.findByLabelText('Đơn vị bán hàng *');
      if (change === 'logout')
        await act(async () => {
          await logout();
        });
      else if (change === 'expiry') {
        api.fetchMock.mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ error: { code: 'AUTH_REQUIRED' } }),
        } as Response);
        await act(async () => {
          await sessionFetch('/api/v1/documents');
        });
      } else {
        api.setUser(beta);
        await act(async () => {
          await refreshSession();
        });
      }
      expect(localStorage.getItem(alphaKey)).toBeNull();
      expect(localStorage.getItem(betaKey)).not.toBeNull();
      if (change !== 'account-change') {
        api.setUser(beta);
        await act(async () => {
          await refreshSession();
        });
      }
      expect(await screen.findByLabelText('Đơn vị bán hàng *')).toHaveValue('Beta private draft');
    },
  );

  it('does not recreate a cleared owner draft when an autosave ACK arrives after account change', async () => {
    const api = server();
    mountSession();
    fireEvent.change(await screen.findByLabelText('Đơn vị bán hàng *'), {
      target: { value: 'Late alpha ACK' },
    });
    let finishSave!: (value: Response) => void;
    api.fetchMock.mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          finishSave = resolve;
        }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Lưu nháp' }));
    api.setUser(beta);
    await act(async () => {
      await refreshSession();
    });
    const next = screen.getByRole('button', { name: 'Xem vùng nguồn: Đơn vị bán hàng' });
    next.focus();
    await act(async () => {
      finishSave({ ok: true, status: 200, json: async () => document(2) } as Response);
    });
    expect(next).toHaveFocus();
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Công ty Mẫu');
    expect(
      Object.keys(localStorage).filter((key) => key.startsWith(ownerPrefix(alpha.id))),
    ).toHaveLength(0);
  });
});

describe('Autosave ordering', () => {
  it('discarding a recovered draft does not delete the source owned by another editor', () => {
    const key = 'field-review:doc:run:tab-a';
    const raw = JSON.stringify({
      at: Date.now(),
      fields: { seller_name: { is_reviewed: true, reviewed_value: 'Tab A' } },
    });
    localStorage.setItem(key, raw);
    render(
      <ReviewPanel
        document={document()}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Tab A');
    fireEvent.click(screen.getByRole('button', { name: 'Bỏ chỉnh sửa' }));
    expect(localStorage.getItem(key)).toBe(raw);
  });
  it('migrates the previous session draft without applying it to the server', () => {
    sessionStorage.setItem(
      'field-review:doc:run',
      JSON.stringify({
        at: Date.now(),
        fields: { seller_name: { is_reviewed: true, reviewed_value: 'Previous session' } },
      }),
    );
    render(
      <ReviewPanel
        document={document()}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Previous session');
    expect(screen.getByRole('alert')).toHaveTextContent('RECOVERED_DRAFT');
    expect(localStorage.getItem('field-review:doc:run:legacy')).not.toBeNull();
  });
  it('ignores expired drafts and never overwrites a newer server from recovery', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn());
    localStorage.setItem(
      'field-review:doc:run:old',
      JSON.stringify({
        at: Date.now() - 86_400_001,
        fields: { seller_name: { is_reviewed: true, reviewed_value: 'Expired' } },
      }),
    );
    const view = render(
      <ReviewPanel
        document={document(5)}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Công ty Mẫu');
    view.unmount();
    localStorage.setItem(
      'field-review:doc:run:old',
      JSON.stringify({
        at: Date.now(),
        fields: { seller_name: { is_reviewed: true, reviewed_value: 'Stale' } },
      }),
    );
    render(
      <ReviewPanel
        document={document(5)}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Stale');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(fetch).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('RECOVERED_DRAFT');
  });
  function mount() {
    return render(
      <ReviewPanel
        document={document()}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
  }
  function edit(value: string) {
    fireEvent.change(screen.getByLabelText('Đơn vị bán hàng *'), { target: { value } });
  }
  it.each([401, 403, 422, 500])(
    'retains draft and stops automatic retries after HTTP %s',
    async (status) => {
      vi.useFakeTimers();
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status,
        json: async () => ({ error: { code: 'REJECTED', message: 'Rejected' } }),
      });
      vi.stubGlobal('fetch', fetchMock);
      mount();
      edit('Keep me');
      await act(async () => {
        await vi.advanceTimersByTimeAsync(800);
      });
      expect(screen.getByRole('alert')).toHaveTextContent('Rejected');
      edit('Keep me too');
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Keep me too');
    },
  );
  it('retains an ambiguous network failure and allows one explicit retry', async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Network failed'))
      .mockResolvedValue({ ok: true, json: async () => document(2) });
    vi.stubGlobal('fetch', fetchMock);
    mount();
    edit('Retry');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(800);
    });
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Retry');
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Lưu nháp' }));
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).expected_revision).toBe(1);
  });
  it('does not autosave edits to a confirmed review until explicit manual save', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => document(2) });
    vi.stubGlobal('fetch', fetchMock);
    const confirmed = document();
    confirmed.review!.review_status = 'confirmed';
    render(
      <ReviewPanel
        document={confirmed}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
    edit('Reopened');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(fetchMock).not.toHaveBeenCalled();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Lưu nháp' }));
    });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).expected_status).toBe('confirmed');
  });
  it('debounces edits and does not create a save loop', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => document(2) });
    vi.stubGlobal('fetch', fetchMock);
    mount();
    edit('A');
    edit('AB');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(799);
    });
    expect(fetchMock).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).fields.seller_name.reviewed_value).toBe(
      'AB',
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it('keeps typing enabled during save and serializes the newer snapshot after ACK', async () => {
    vi.useFakeTimers();
    let resolve!: (value: unknown) => void;
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((r) => {
            resolve = r;
          }),
      )
      .mockResolvedValue({ ok: true, json: async () => document(3) });
    vi.stubGlobal('fetch', fetchMock);
    mount();
    edit('A');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(800);
    });
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toBeEnabled();
    edit('AB');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1600);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async () => {
      resolve({ ok: true, json: async () => document(2) });
    });
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('AB');
    expect(screen.getByRole('button', { name: 'Xác nhận bản lưu' })).toBeDisabled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(800);
    });
    const body = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(body.expected_revision).toBe(2);
    expect(body.fields.seller_name.reviewed_value).toBe('AB');
  });
  it('recovers edits after unmount without sending a background write', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn());
    const view = mount();
    edit('Draft');
    view.unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1600);
    });
    expect(fetch).not.toHaveBeenCalled();
    mount();
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Draft');
    expect(screen.getByRole('button', { name: 'Xác nhận bản lưu' })).toBeDisabled();
  });
});

describe('Review product data', () => {
  it('sends explicit null and disables confirm until edits are saved', async () => {
    const updated = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => document(2) }));
    render(
      <ReviewPanel
        document={document()}
        onUpdated={updated}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Xóa giá trị' }));
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Xác nhận bản lưu' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Lưu nháp' }));
    await waitFor(() => expect(updated).toHaveBeenCalled());
    const body = JSON.parse(vi.mocked(fetch).mock.calls[0][1]!.body as string);
    expect(body.fields.seller_name).toEqual({ is_reviewed: true, reviewed_value: null });
    expect(body.expected_revision).toBe(1);
  });

  it('retains user edits on 409 and compares server values before rebasing', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({ error: { code: 'REVISION_CONFLICT', message: 'Bản đã thay đổi' } }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => document(2) })
      .mockResolvedValueOnce({ ok: true, json: async () => document(3) });
    vi.stubGlobal('fetch', fetchMock);
    render(
      <ReviewPanel
        document={document()}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText('Đơn vị bán hàng *'), {
      target: { value: 'Bản của tôi' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Lưu nháp' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Bản đã thay đổi');
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toHaveValue('Bản của tôi');
    fireEvent.click(screen.getByRole('button', { name: 'Đối chiếu bản mới' }));
    fireEvent.click(
      await screen.findByRole('button', { name: 'Giữ chỉnh sửa, dùng revision mới' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Lưu nháp' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const body = JSON.parse(fetchMock.mock.calls[2][1].body);
    expect(body.expected_revision).toBe(2);
    expect(body.fields.seller_name.reviewed_value).toBe('Bản của tôi');
  });

  it('old runs are read-only and cannot export or overwrite current review', () => {
    render(
      <ReviewPanel
        document={{ ...document(), is_latest_run: false }}
        onUpdated={vi.fn()}
        onDirtyChange={vi.fn()}
        onFieldChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('Đơn vị bán hàng *')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Lưu nháp' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Xuất JSON đã xác nhận' })).toBeDisabled();
  });
});
