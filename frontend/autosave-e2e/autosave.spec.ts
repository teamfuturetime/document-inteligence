import { expect, test, chromium, type Page } from '@playwright/test';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
let sequence = 0;
let index = 0;
async function open(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
  await page.getByRole('button', { name: 'Mở tài liệu', exact: true }).nth(index).click();
  await expect(page.locator('#field-seller_name')).toBeEnabled();
}
const seller = (page: Page) => page.locator('#field-seller_name');
const confirm = (page: Page) => page.getByRole('button', { name: 'Xác nhận bản lưu', exact: true });
async function saved(page: Page) {
  await expect(page.getByText('Đã lưu nháp trên máy chủ.', { exact: true })).toBeVisible();
}
test.beforeEach(() => {
  index = sequence++;
});
test('duplicated tab keeps separate pending browser drafts', async ({ page }) => {
  await open(page);
  const popupEvent = page.waitForEvent('popup');
  await page.evaluate(() => window.open('/'));
  const popup = await popupEvent;
  await open(popup);
  await page.context().route('**/api/v1/documents/*/review', (route) => route.abort());
  await seller(page).fill('Original tab draft');
  await seller(popup).fill('Duplicated tab draft');
  const drafts = await page.evaluate(() =>
    Object.keys(localStorage)
      .filter((key) => key.startsWith('field-review:'))
      .map((key) => localStorage.getItem(key)),
  );
  expect(drafts.join('\n')).toContain('Original tab draft');
  expect(drafts.join('\n')).toContain('Duplicated tab draft');
});
test('1 debounce autosave', async ({ page }) => {
  await open(page);
  let writes = 0;
  page.on('request', (r) => {
    if (r.method() === 'PUT' && r.url().endsWith('/review')) writes++;
  });
  await seller(page).fill('Debounce A');
  await seller(page).fill('Debounce AB');
  await saved(page);
  expect(writes).toBe(1);
  await page.waitForTimeout(1000);
  expect(writes).toBe(1);
});
test('2 two tabs and 3 real HTTP409 retain edits until comparison', async ({ page, context }) => {
  await open(page);
  const other = await context.newPage();
  await open(other);
  await seller(page).fill('Server winner');
  await saved(page);
  await seller(other).fill('Local loser');
  await expect(other.getByRole('alert')).toContainText('REVISION_CONFLICT');
  await expect(seller(other)).toHaveValue('Local loser');
  await other.getByRole('button', { name: 'Đối chiếu bản mới' }).click();
  await expect(other.locator('.conflict-box')).toContainText('Server winner');
  await other.waitForTimeout(1200);
  await other.getByRole('button', { name: 'Bỏ chỉnh sửa, tải bản máy chủ' }).click();
  await expect(seller(other)).toHaveValue('Server winner');
});
test('4 actual fetch timeout and manual retry', async ({ page }) => {
  await open(page);
  await page.route('**/api/v1/documents/*/review', async (route) => {
    await new Promise((r) => setTimeout(r, 17000));
    await route.abort().catch(() => {});
  });
  await seller(page).fill('Timeout draft');
  await expect(page.getByRole('alert')).toBeVisible({ timeout: 22000 });
  await expect(seller(page)).toHaveValue('Timeout draft');
  await page.unroute('**/api/v1/documents/*/review');
  await page.getByRole('button', { name: 'Lưu nháp', exact: true }).click();
  await saved(page);
});
test('5 unsaved navigation is blocked', async ({ page }) => {
  await open(page);
  await seller(page).fill('Navigation draft');
  await page.getByRole('button', { name: 'Giới thiệu', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('trước khi chuyển trang');
  await expect(seller(page)).toHaveValue('Navigation draft');
  await saved(page);
});
test('6 confirm and manual save blocked inflight; ACK retains newer edit', async ({ page }) => {
  await open(page);
  let release!: () => void;
  const gate = new Promise<void>((r) => {
    release = r;
  });
  await page.route('**/api/v1/documents/*/review', async (route) => {
    await gate;
    await route.continue();
  });
  await seller(page).fill('Inflight A');
  await expect(page.getByText('Đang lưu nháp…', { exact: true })).toBeVisible();
  await expect(confirm(page)).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Lưu nháp', exact: true })).toBeDisabled();
  await seller(page).fill('Inflight AB');
  release();
  await saved(page);
  await expect(seller(page)).toHaveValue('Inflight AB');
  await expect(confirm(page)).toBeEnabled();
});
test('7 reload recovery pauses writes', async ({ page }) => {
  await open(page);
  await seller(page).fill('Reload draft');
  await page.reload();
  await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
  await page.getByRole('button', { name: 'Mở tài liệu', exact: true }).nth(index).click();
  await expect(seller(page)).toHaveValue('Reload draft');
  await expect(page.getByRole('alert')).toContainText('RECOVERED_DRAFT');
  await expect(confirm(page)).toBeDisabled();
  await page.getByRole('button', { name: 'Đối chiếu bản mới' }).click();
  await page.getByRole('button', { name: 'Giữ chỉnh sửa, dùng revision mới' }).click();
  await saved(page);
});
test('browser process restart recovers pending draft', async () => {
  const profile = await mkdtemp(join(tmpdir(), 'review-recovery-'));
  let context = await chromium.launchPersistentContext(profile, {
    headless: true,
    baseURL: 'http://127.0.0.1:15174',
  });
  try {
    let page = await context.newPage();
    await open(page);
    await seller(page).fill('Restart draft');
    await context.close();
    context = await chromium.launchPersistentContext(profile, {
      headless: true,
      baseURL: 'http://127.0.0.1:15174',
    });
    page = await context.newPage();
    await open(page);
    await expect(seller(page)).toHaveValue('Restart draft');
    await expect(page.getByRole('alert')).toContainText('RECOVERED_DRAFT');
    await expect(confirm(page)).toBeDisabled();
  } finally {
    await context.close();
    await rm(profile, { recursive: true, force: true });
  }
});
test('stale recovered draft never automatically replaces newer persisted server data', async ({
  page,
}) => {
  await open(page);
  await seller(page).fill('Stale local');
  await page.reload();
  const list = await (await page.request.get('/api/v1/documents')).json();
  const path = `/api/v1/documents/${list.items[index].document_id}`;
  const detail = await (await page.request.get(path)).json();
  const savedServer = await page.request.put(path + '/review', {
    data: {
      run_id: detail.run.run_id,
      expected_revision: detail.review.revision,
      expected_status: 'draft',
      fields: { seller_name: { is_reviewed: true, reviewed_value: 'Newer server' } },
    },
  });
  expect(savedServer.status()).toBe(200);
  await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
  await page.getByRole('button', { name: 'Mở tài liệu', exact: true }).nth(index).click();
  await expect(seller(page)).toHaveValue('Stale local');
  await page.waitForTimeout(1200);
  expect((await (await page.request.get(path)).json()).review.effective_data.seller_name).toBe(
    'Newer server',
  );
  await page.getByRole('button', { name: 'Đối chiếu bản mới' }).click();
  await expect(page.locator('.conflict-box')).toContainText('Newer server');
  await page.getByRole('button', { name: 'Bỏ chỉnh sửa, tải bản máy chủ' }).click();
  await expect(seller(page)).toHaveValue('Newer server');
});
test('8 export uses confirmed persisted revision', async ({ page }) => {
  await open(page);
  await seller(page).fill('Export seller');
  await saved(page);
  await confirm(page).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Xuất JSON đã xác nhận', exact: true }).click();
  const file = await download;
  const stream = await file.createReadStream();
  let json = '';
  for await (const chunk of stream!) json += chunk.toString();
  const value = JSON.parse(json);
  expect(value.data.seller_name).toBe('Export seller');
  expect(value.revision).toBe(2);
});
