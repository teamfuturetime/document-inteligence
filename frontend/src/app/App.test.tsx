import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import fixture from '../../../contracts/examples/fixture-view.json';
import { App } from './App';

const capabilities = {
  provider_mode: 'fixture',
  ocr_ready: false,
  supported_schemas: ['don_de_nghi@1.0.0'],
  model_benchmark_status: 'not_measured',
  features: { export: 'planned' },
};
function mockAPI(options: { mode?: string; empty?: boolean } = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      let value: unknown;
      if (path.endsWith('/capabilities'))
        value = { ...capabilities, provider_mode: options.mode ?? 'fixture' };
      else if (path.endsWith('/fixtures'))
        value = { prediction_source: 'fixture', sample_ids: options.empty ? [] : ['fixture_001'] };
      else value = fixture;
      return { ok: true, json: async () => value };
    }),
  );
}
afterEach(() => vi.unstubAllGlobals());

describe('Giao diện foundation trung thực', () => {
  it('ghi rõ fixture và khóa chức năng chưa triển khai', async () => {
    mockAPI();
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Mẫu minh họa' }));
    expect(await screen.findByDisplayValue('Nguyễn Minh An')).toHaveAttribute('readonly');
    expect(screen.getByText('Mẫu giả lập — chưa chạy OCR')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Xuất JSON' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Xác nhận' })).toBeDisabled();
    expect(screen.getByText(/Một số dự đoán sai có chủ ý/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Xem bằng chứng: Họ và tên' }));
    expect(
      screen
        .getByRole('img', { name: 'Vùng bằng chứng của trường đang chọn' })
        .querySelector('polygon'),
    ).not.toBeNull();
  });

  it('chế độ unconfigured không tự fallback sang fixture', async () => {
    mockAPI({ mode: 'unconfigured' });
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Mẫu minh họa' }));
    expect(await screen.findByText(/Chế độ fixture chưa bật/)).toBeVisible();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(
      vi.mocked(fetch).mock.calls.every(([path]) => String(path).endsWith('/capabilities')),
    ).toBe(true);
  });

  it('cho biết lỗi backend và tải lại sau khi sửa kết nối', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Mất kết nối')));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Không kết nối được backend');
    mockAPI();
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByText(/Provider: fixture/)).toBeVisible();
  });

  it('hiển thị catalogue trống', async () => {
    mockAPI({ empty: true });
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Mẫu minh họa' }));
    expect(await screen.findByText('Chưa có mẫu minh họa.')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Xuất JSON' })).not.toBeInTheDocument();
  });
});
