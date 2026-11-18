import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const baseURL = 'http://127.0.0.1:15174';
const image = fileURLToPath(new URL('../../data/product/images/hoa_don_007.png', import.meta.url));
async function workspace(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
}
async function login(page: Page, username: string) {
  await page.getByLabel('Tên đăng nhập').fill(username);
  await page.getByLabel('Mật khẩu', { exact: true }).fill('synthetic-browser-password-123');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText(username);
}
async function upload(page: Page) {
  await page.getByLabel('Ảnh PNG/JPG một trang').setInputFiles(image);
  await page.getByRole('checkbox', { name: /Tôi xác nhận/ }).check();
  await page.getByRole('button', { name: 'Tải lên và nhận dạng', exact: true }).click();
  await expect(page.locator('#field-seller_name')).toBeEnabled({ timeout: 45_000 });
  const list = await (await page.request.get('/api/v1/documents')).json();
  const document = await (
    await page.request.get(`/api/v1/documents/${list.items[0].document_id}`)
  ).json();
  expect(document.run.metadata.prediction_source).toBe('model');
  return document;
}

test('two accounts: native review/export, foreign identifiers, independent cookies and logout', async ({
  browser,
}) => {
  const alpha = await browser.newContext({ baseURL });
  const beta = await browser.newContext({ baseURL });
  try {
    const first = await alpha.newPage();
    const second = await beta.newPage();
    await workspace(first);
    expect((await first.request.get('/api/v1/documents')).status()).toBe(401);
    await login(first, 'alpha');
    const doc = await upload(first);
    const prediction = doc.run.fields;
    const visible = {
      invoice_number: '0041007',
      invoice_date: '2026-10-08',
      seller_name: 'Công ty Giả Lập 107',
      total_amount: '1000000',
      currency: 'VND',
    };
    for (const [field, value] of Object.entries(visible))
      await first.locator(`#field-${field}`).fill(value);
    const review = first.getByRole('region', { name: 'Kiểm tra và sửa kết quả' });
    for (const checkbox of await review
      .getByRole('checkbox', { name: 'Đã đối chiếu trường này', exact: true })
      .all())
      await checkbox.check();
    await review.getByRole('button', { name: 'Lưu nháp', exact: true }).click();
    await expect(review.getByText('Đã lưu nháp trên máy chủ.', { exact: true })).toBeVisible();
    await review.getByRole('button', { name: 'Xác nhận bản lưu', exact: true }).click();
    const downloadPromise = first.waitForEvent('download');
    await review.getByRole('button', { name: 'Xuất JSON đã xác nhận', exact: true }).click();
    const download = await downloadPromise;
    const exported = JSON.parse(await readFile((await download.path())!, 'utf8'));
    expect(exported.data).toEqual({ ...visible, total_amount: 1000000 });
    const latest = await (await first.request.get(`/api/v1/documents/${doc.document_id}`)).json();
    expect(latest.run.fields).toEqual(prediction);

    await workspace(second);
    await login(second, 'beta');
    await expect(
      second.getByText('Chưa có tài liệu phù hợp. Hãy tải ảnh sample đầu tiên.'),
    ).toBeVisible();
    for (const suffix of [
      '',
      '/image',
      '/history',
      `/export?run_id=${doc.run.run_id}&revision=${latest.review.revision}`,
    ]) {
      expect(
        (await second.request.get(`/api/v1/documents/${doc.document_id}${suffix}`)).status(),
      ).toBe(404);
    }
    const session = await (await second.request.get('/api/v1/auth/session')).json();
    expect(
      (
        await second.request.put(`/api/v1/documents/${doc.document_id}/review`, {
          data: { run_id: doc.run.run_id, expected_revision: latest.review.revision, fields: {} },
          headers: { 'X-CSRF-Token': session.csrf_token, Origin: baseURL },
        })
      ).status(),
    ).toBe(404);
    expect((await (await second.request.get('/api/v1/insights')).json()).documents).toBe(0);
    const own = await upload(second);
    expect(own.document_id).not.toBe(doc.document_id);
    expect((await (await first.request.get('/api/v1/documents')).json()).total).toBe(1);
    await first.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
    await expect(first.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
    await expect(first.getByRole('region', { name: 'Kiểm tra và sửa kết quả' })).toHaveCount(0);
    expect((await first.request.get('/api/v1/documents')).status()).toBe(401);
    expect((await second.request.get('/api/v1/documents')).status()).toBe(200);
  } finally {
    await alpha.close();
    await beta.close();
  }
});

test('shared cookie changes clear another tab, and revoked sessions remove the workspace', async ({
  browser,
}) => {
  const context = await browser.newContext({ baseURL });
  try {
    const first = await context.newPage();
    await workspace(first);
    await login(first, 'gamma');
    const doc = await upload(first);
    const second = await context.newPage();
    await workspace(second);
    await expect(second.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText('gamma');
    await second.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
    await expect(first.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
    await expect(first.locator('#field-seller_name')).toHaveCount(0);
    await login(second, 'delta');
    await expect(first.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText('delta');
    expect((await first.request.get(`/api/v1/documents/${doc.document_id}`)).status()).toBe(404);
    await upload(first);
    const session = await (await first.request.get('/api/v1/auth/session')).json();
    expect(
      (
        await first.request.post('/api/v1/auth/logout', {
          headers: { 'X-CSRF-Token': session.csrf_token, Origin: baseURL },
        })
      ).status(),
    ).toBe(204);
    await first.getByRole('button', { name: 'Tải bản mới nhất', exact: true }).click();
    await expect(first.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
    await expect(first.locator('#field-seller_name')).toHaveCount(0);
  } finally {
    await context.close();
  }
});
