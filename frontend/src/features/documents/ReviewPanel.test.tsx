import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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

afterEach(() => vi.unstubAllGlobals());

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
