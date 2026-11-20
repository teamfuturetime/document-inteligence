import { expect, test, type Page } from '@playwright/test';
import ready from '../../contracts/examples/readiness-ready.json' with { type: 'json' };
import notReady from '../../contracts/examples/readiness-not-ready.json' with { type: 'json' };
import type { DocumentDetail } from '../src/features/documents/api';

// Explicit HTTP/session/inference doubles. Native health/readiness/ownership
// continue to run in the existing backend, native and authenticated CI suites.
async function backend(page: Page) {
  let phase: 'ready' | 'not_ready' | 'offline' = 'not_ready';
  let owner = 'alpha';
  let expired = false;
  let failUpload = true;
  let holdList: (() => Promise<void>) | null = null;
  const documents = new Map<string, DocumentDetail>();
  for (const name of ['alpha', 'beta'])
    documents.set(name, {
      document_id: `${name}-doc`,
      document_type: 'hoa_don',
      filename: `${name}-synthetic.png`,
      data_origin: 'synthetic',
      input_sha256: 'a'.repeat(64),
      image_width: 100,
      image_height: 100,
      created_at: '2026-11-20T00:00:00Z',
      latest_run_id: `${name}-run`,
      status: 'succeeded',
      image_url: '/readiness-image',
      is_latest_run: true,
      definitions: [
        { field_id: 'seller_name', label: 'Đơn vị bán hàng', value_type: 'text', required: true },
      ],
      run: {
        run_id: `${name}-run`,
        status: 'succeeded',
        created_at: '2026-11-20T00:00:00Z',
        fields: [],
        spans: [],
      },
      review: {
        revision: 1,
        review_status: 'draft',
        saved_at: '2026-11-20T00:00:00Z',
        fields: { seller_name: { is_reviewed: false, reviewed_value: null } },
        effective_data: { seller_name: `${name} seller` },
        validation_issues: [],
      },
    });
  const stats = {
    readiness: 0,
    capabilities: 0,
    sessions: 0,
    uploads: 0,
    reviews: 0,
    keys: [] as string[],
  };
  await page.route('**/readiness-image?*', (route) =>
    route.fulfill({
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg"/>',
    }),
  );
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    const observedOwner = owner;
    const doc = documents.get(observedOwner)!;
    if (path.endsWith('/readiness')) stats.readiness++;
    if (path.endsWith('/auth/session')) stats.sessions++;
    if (phase === 'offline') return route.abort('internetdisconnected');
    if (path.endsWith('/readiness'))
      return route.fulfill({
        status: phase === 'ready' ? 200 : 503,
        json: { ...(phase === 'ready' ? ready : notReady), auth_mode: 'session' },
      });
    if (path.endsWith('/auth/session'))
      return route.fulfill(
        expired
          ? { status: 401, json: { error: { code: 'AUTH_REQUIRED', message: 'Session expired' } } }
          : {
              json: {
                mode: 'session',
                user: { id: (owner === 'alpha' ? 'a' : 'b').repeat(32), username: owner },
                csrf_token: owner + '-csrf',
              },
            },
      );
    if (path.endsWith('/capabilities')) {
      stats.capabilities++;
      return route.fulfill({
        json: {
          features: {},
          max_upload_bytes: 5242880,
          model_benchmark_status: 'not_measured',
          ocr_ready: true,
          provider_mode: 'tesseract',
          supported_schemas: [],
        },
      });
    }
    if (path.endsWith('/document-schemas')) return route.fulfill({ json: [] });
    if (path.endsWith('/insights')) return route.fulfill({ json: { documents: 1 } });
    if (path.endsWith('/history')) return route.fulfill({ json: { runs: [], events: [] } });
    if (path.endsWith('/documents')) {
      if (route.request().method() === 'POST') {
        stats.uploads++;
        stats.keys.push(route.request().headers()['idempotency-key']);
        if (failUpload) {
          failUpload = false;
          return route.abort('internetdisconnected');
        }
        return route.fulfill({ json: doc });
      }
      if (holdList) {
        const gate = holdList;
        holdList = null;
        await gate();
      }
      return route
        .fulfill({ json: { items: [doc], total: 1, offset: 0, limit: 10 } })
        .catch(() => {});
    }
    if (path.endsWith('/review')) {
      stats.reviews++;
      const body = route.request().postDataJSON();
      expect(route.request().headers()['x-csrf-token']).toBe(observedOwner + '-csrf');
      expect(body.run_id).toBe(doc.run.run_id);
      expect(body.expected_revision).toBe(doc.review!.revision);
      expect(body.expected_status).toBe('draft');
      const next = {
        ...doc,
        review: {
          ...doc.review!,
          revision: doc.review!.revision + 1,
          fields: body.fields,
          effective_data: { seller_name: body.fields.seller_name.reviewed_value },
        },
      };
      documents.set(observedOwner, next);
      return route.fulfill({ json: next });
    }
    if (path.endsWith(`/${observedOwner}-doc`)) return route.fulfill({ json: doc });
    return route.fulfill({
      status: 404,
      json: { error: { code: 'NOT_FOUND', message: 'Not found' } },
    });
  });
  return {
    stats,
    documents,
    phase: (next: typeof phase) => {
      phase = next;
    },
    owner: (next: string) => {
      owner = next;
    },
    expire: () => {
      expired = true;
    },
    hold: (gate: () => Promise<void>) => {
      holdList = gate;
    },
  };
}

async function open(page: Page) {
  await page.getByRole('button', { name: 'Mở tài liệu', exact: true }).click();
  await expect(page.getByLabel('Đơn vị bán hàng *')).toBeEnabled();
}
const status = (page: Page) => page.getByRole('status', { name: 'Trạng thái backend' });
const stored = (page: Page) =>
  page.evaluate(() =>
    Object.fromEntries(
      Object.keys(localStorage)
        .filter((key) => key.startsWith('field-review:'))
        .map((key) => [key, localStorage.getItem(key)]),
    ),
  );

for (const width of [1280, 390])
  test(`disconnect/reconnect keeps null draft and never replays uploads/writes at ${width}px (HTTP doubles)`, async ({
    page,
    context,
  }) => {
    await page.setViewportSize({ width, height: 850 });
    const api = await backend(page);
    await page.clock.install();
    await page.goto('/');
    await expect(status(page)).toContainText('Chưa sẵn sàng');
    await page.clock.pauseAt(new Date());
    await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText('alpha');
    await page.getByLabel('Ảnh PNG/JPG một trang').setInputFiles({
      name: 'synthetic.png',
      mimeType: 'image/png',
      buffer: Buffer.from('synthetic'),
    });
    await page.getByRole('checkbox', { name: /Tôi xác nhận/ }).check();
    const upload = page.getByRole('button', { name: 'Tải lên và nhận dạng', exact: true });
    await expect(upload).toBeDisabled();
    api.phase('ready');
    await page.getByRole('button', { name: 'Thử lại', exact: true }).click();
    await page.clock.runFor(1000);
    await expect(status(page)).toContainText('Sẵn sàng —');
    await expect(upload).toBeEnabled();
    const capBefore = api.stats.capabilities;
    await upload.click();
    await expect(page.getByRole('alert')).toContainText('Mất kết nối khi tải ảnh');
    expect(api.stats.uploads).toBe(1);
    await open(page);
    api.phase('offline');
    await context.setOffline(true);
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await expect(page.getByRole('status', { name: 'Xác minh phiên' })).toBeVisible();
    await expect(status(page)).toContainText('Đang kết nối lại');
    const input = page.getByLabel('Đơn vị bán hàng *');
    await input.fill('');
    await expect(input).toBeEnabled();
    expect(JSON.stringify(await stored(page))).toContain('reviewed_value');
    expect(
      Object.keys(await stored(page)).every((key) =>
        key.startsWith('field-review:user:' + 'a'.repeat(32)),
      ),
    ).toBe(true);
    const before = api.stats.readiness;
    await page.clock.runFor(15000);
    await expect.poll(() => api.stats.readiness).toBe(before + 1);
    await page.clock.runFor(1000);
    await expect.poll(() => api.stats.readiness).toBe(before + 2);
    expect(api.stats.capabilities).toBe(capBefore);
    expect(api.stats.uploads).toBe(1);
    expect(api.stats.reviews).toBe(0);
    api.phase('not_ready');
    await context.setOffline(false);
    await page.getByRole('button', { name: 'Thử lại', exact: true }).click();
    await page.clock.runFor(1000);
    await expect(status(page)).toContainText('Chưa sẵn sàng');
    await expect(page.getByRole('button', { name: 'Thử tải lại', exact: true })).toBeDisabled();
    await expect(input).toHaveValue('');
    api.phase('ready');
    await page.getByRole('button', { name: 'Thử lại', exact: true }).click();
    await page.clock.runFor(1000);
    await expect(status(page)).toContainText('Sẵn sàng —');
    expect(api.stats.capabilities).toBeGreaterThan(capBefore);
    await page.clock.runFor(5000);
    expect(api.stats.reviews).toBe(0);
    expect(api.stats.uploads).toBe(1);
    await expect(input).toHaveValue('');
    await page.getByRole('button', { name: 'Lưu nháp', exact: true }).click();
    await expect.poll(() => api.stats.reviews).toBe(1);
    expect(api.documents.get('alpha')!.review!.fields.seller_name).toEqual({
      is_reviewed: true,
      reviewed_value: null,
    });
    await expect(page.getByText('Đã lưu nháp trên máy chủ.', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Thử tải lại', exact: true }).click();
    await expect.poll(() => api.stats.uploads).toBe(2);
    expect(api.stats.keys[1]).toBe(api.stats.keys[0]);
    await expect(status(page)).toHaveAttribute('aria-live', 'polite');
    expect(api.stats.readiness - before).toBeLessThanOrEqual(5);
  });

test('late owner response cannot repopulate workspace; verified 401 clears only current owner (HTTP doubles)', async ({
  page,
}) => {
  const api = await backend(page);
  api.phase('ready');
  await page.goto('/');
  await expect(status(page)).toContainText('Sẵn sàng —');
  await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
  await open(page);
  await page.getByLabel('Đơn vị bán hàng *').fill('Alpha private pending');
  await expect
    .poll(async () => JSON.stringify(await stored(page)))
    .toContain('Alpha private pending');
  let release!: () => void;
  let started!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  const observed = new Promise<void>((resolve) => {
    started = resolve;
  });
  api.hold(async () => {
    started();
    await held;
  });
  await page.getByRole('combobox', { name: 'Trạng thái', exact: true }).selectOption('succeeded');
  await observed;
  api.owner('beta');
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText('beta');
  release();
  await expect(page.getByRole('row', { name: /beta-synthetic.png/ })).toBeVisible();
  await expect(page.getByRole('row', { name: /alpha-synthetic.png/ })).toHaveCount(0);
  expect(Object.keys(await stored(page)).some((key) => key.includes('a'.repeat(32)))).toBe(false);
  await open(page);
  await page.getByLabel('Đơn vị bán hàng *').fill('Beta private pending');
  api.expire();
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
  await expect(page.getByLabel('Đơn vị bán hàng *')).toHaveCount(0);
  expect(Object.keys(await stored(page))).toHaveLength(0);
});
