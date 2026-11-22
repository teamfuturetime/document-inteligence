import { expect, test } from '@playwright/test';
import { capabilities, errorDocument, processedDocument } from './error-fixture';

test('failed OCR requires explicit keyboard retry before review (HTTP/inference doubles)', async ({
  page,
}) => {
  let document = errorDocument();
  let writes = 0;
  await page.route(/\/image\?/, (route) =>
    route.fulfill({
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="white"/></svg>',
    }),
  );
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let value: unknown = document;
    if (path.endsWith('/auth/session')) value = { mode: 'local', user: null, csrf_token: null };
    else if (path.endsWith('/capabilities')) value = capabilities;
    else if (path.endsWith('/document-schemas')) value = [];
    else if (path.endsWith('/insights')) value = { documents: 1 };
    else if (path.endsWith('/history')) value = { runs: [], events: [] };
    else if (path.endsWith('/documents'))
      value = { items: [document], total: 1, offset: 0, limit: 10 };
    else if (path.endsWith('/runs')) {
      expect(route.request().method()).toBe('POST');
      expect(route.request().postDataJSON()).toEqual({ expected_run_id: 'old' });
      writes++;
      document = processedDocument();
      value = document;
    }
    await route.fulfill({ json: value });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
  await page.getByRole('button', { name: 'Mở tài liệu' }).click();
  await expect(page.getByRole('alert')).toContainText('OCR vượt thời gian');
  await page.waitForTimeout(1500);
  expect(writes).toBe(0);
  const retry = page.getByRole('button', { name: 'Chạy OCR lại', exact: true });
  await retry.focus();
  await expect(retry).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#field-seller_name')).toBeEnabled();
  await expect(page.locator('#field-seller_name')).toHaveValue('');
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(writes).toBe(1);
});
