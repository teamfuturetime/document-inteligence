import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { Workspace } from './Workspace';

function response(value: unknown) {
  return new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' } });
}

afterEach(() => vi.unstubAllGlobals());

it('navigates tied document pages in server order without duplicates on a fixed dataset', async () => {
  const items = Array.from({ length: 12 }, (_, index) => {
    const id = (12 - index).toString(16);
    return {
      document_id: id.repeat(32),
      document_type: 'hoa_don',
      filename: `invoice-${id}.png`,
      data_origin: 'synthetic',
      input_sha256: 'a'.repeat(64),
      image_width: 300,
      image_height: 200,
      created_at: '2026-11-19T00:00:00Z',
      latest_run_id: id.repeat(32),
      status: 'queued',
      review_status: null,
    };
  });
  const offsets: number[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const { pathname, searchParams } = new URL(url, 'http://localhost');
      if (pathname === '/api/v1/document-schemas') return response([]);
      if (pathname === '/api/v1/insights') return response({ documents: 12 });
      if (pathname === '/api/v1/documents') {
        const offset = Number(searchParams.get('offset'));
        expect(searchParams.get('limit')).toBe('10');
        offsets.push(offset);
        return response({ items: items.slice(offset, offset + 10), total: 12, limit: 10, offset });
      }
      throw new Error(`Unexpected request: ${pathname}`);
    }),
  );
  render(
    <Workspace
      capabilities={{
        features: {},
        max_upload_bytes: 5_242_880,
        model_benchmark_status: 'not_measured',
        ocr_ready: true,
        provider_mode: 'tesseract',
        supported_schemas: [],
      }}
      onUnsavedChange={vi.fn()}
    />,
  );
  const names = () =>
    within(screen.getByRole('table'))
      .getAllByText(/^invoice-[0-9a-f]\.png$/)
      .map((node) => node.textContent?.match(/invoice-[0-9a-f]\.png/)?.[0]);
  await screen.findByText('invoice-c.png');
  const first = names();
  expect(first).toEqual(items.slice(0, 10).map((item) => item.filename));
  expect(screen.getByRole('button', { name: 'Trang trước' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Trang sau' }));
  await screen.findByText('invoice-1.png');
  const second = names();
  expect(second).toEqual(['invoice-2.png', 'invoice-1.png']);
  expect(new Set([...first, ...second]).size).toBe(12);
  expect(screen.getByRole('button', { name: 'Trang sau' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Trang trước' }));
  await screen.findByText('invoice-c.png');
  expect(names()).toEqual(first);
  expect(offsets).toEqual([0, 10, 0]);
});
