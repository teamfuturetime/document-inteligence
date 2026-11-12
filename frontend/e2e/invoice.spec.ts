import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

test('native invoice: upload, missing draft, persisted edit, conflict, confirm and JSON download', async ({
  page,
}) => {
  const ready = await page.request.get('/api/v1/capabilities');
  expect((await ready.json()).ocr_ready).toBe(true);
  await page.goto('/');
  await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
  await page
    .getByLabel('Ảnh PNG/JPG một trang')
    .setInputFiles(
      fileURLToPath(new URL('../../data/product/images/hoa_don_007.png', import.meta.url)),
    );
  await page.getByRole('checkbox', { name: /Tôi xác nhận/ }).check();
  await page.getByRole('button', { name: 'Tải lên và nhận dạng', exact: true }).click();
  const review = page.getByRole('region', { name: 'Kiểm tra và sửa kết quả' });
  const seller = page.locator('#field-seller_name');
  await expect(seller).toBeEnabled({ timeout: 40_000 });
  const source = await page.request.get('/api/v1/documents');
  const doc = (await source.json()).items[0];
  let detail = await (await page.request.get(`/api/v1/documents/${doc.document_id}`)).json();
  expect(detail.run.status).toBe('succeeded');
  expect(detail.run.metadata.prediction_source).toBe('model');
  expect(detail.run.spans.length).toBeGreaterThan(0);
  const originalPrediction = detail.run.fields;

  // Required null survives save/reload; confirmation stays blocked.
  await seller.fill('');
  await review.getByRole('button', { name: 'Lưu nháp', exact: true }).click();
  await expect(
    review.getByRole('button', { name: 'Xác nhận bản lưu', exact: true }),
  ).toBeDisabled();
  await expect(review.getByText('Đã lưu nháp trên máy chủ.', { exact: true })).toBeVisible();
  detail = await (await page.request.get(`/api/v1/documents/${doc.document_id}`)).json();
  expect(detail.review.effective_data.seller_name).toBeNull();
  const staleRevision = detail.review.revision;
  await page.reload();
  await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
  await page.getByRole('button', { name: 'Mở tài liệu', exact: true }).click();
  await expect(seller).toHaveValue('');

  // Visible development-sample values are a scripted review, not a prediction metric.
  const visible = {
    invoice_number: '0041007',
    invoice_date: '2026-10-08',
    seller_name: 'Công ty Giả Lập 107',
    total_amount: '1000000',
    currency: 'VND',
  };
  for (const [field, value] of Object.entries(visible)) {
    await page.locator(`#field-${field}`).fill(value);
  }
  await review.getByRole('button', { name: 'Lưu nháp', exact: true }).click();
  await expect(review.getByText('Đã lưu nháp trên máy chủ.', { exact: true })).toBeVisible();
  const stale = await page.request.put(`/api/v1/documents/${doc.document_id}/review`, {
    data: {
      run_id: detail.run.run_id,
      expected_revision: staleRevision,
      fields: { seller_name: { is_reviewed: true, reviewed_value: 'Stale write' } },
    },
  });
  expect(stale.status()).toBe(409);
  await review.getByRole('button', { name: 'Xác nhận bản lưu', exact: true }).click();
  const exportButton = review.getByRole('button', { name: 'Xuất JSON đã xác nhận', exact: true });
  await expect(exportButton).toBeEnabled();
  const downloaded = page.waitForEvent('download');
  await exportButton.click();
  const download = await downloaded;
  const path = await download.path();
  expect(path).not.toBeNull();
  const exported = JSON.parse(await readFile(path!, 'utf8'));
  expect(exported.document_type).toBe('hoa_don');
  expect(exported.data).toEqual({ ...visible, total_amount: 1000000 });
  detail = await (await page.request.get(`/api/v1/documents/${doc.document_id}`)).json();
  expect(exported.revision).toBe(detail.review.revision);
  expect(detail.review.review_status).toBe('confirmed');
  expect(detail.run.fields).toEqual(originalPrediction);
  await page.screenshot({ path: 'test-results/invoice-confirmed.png', fullPage: true });
});
