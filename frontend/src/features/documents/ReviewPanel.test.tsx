import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ReviewPanel } from './ReviewPanel';
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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  sessionStorage.clear();
});

describe('Autosave ordering', () => {
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
