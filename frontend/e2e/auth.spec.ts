import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const baseURL = 'http://127.0.0.1:15174';
const image = fileURLToPath(new URL('../../data/product/images/hoa_don_007.png', import.meta.url));

// Native PDF and real HTTP/SQLite. Only response delivery is held to exercise late ACKs.
test('PDF session: autosave ACK, null, conflict, confirmed export and foreign owner', async ({
  browser,
}) => {
  const owner = await browser.newContext({ baseURL });
  const foreign = await browser.newContext({ baseURL });
  let release!: () => void;
  try {
    const page = await owner.newPage();
    await workspace(page);
    await login(page, 'pdfalpha');
    const doc = await upload(page, 'pdf');
    const path = `/api/v1/documents/${doc.document_id}`;
    expect(doc.run.metadata.preprocessing.source_frame).toBe('pdf_raster_pixels_top_left');
    const prediction = doc.run.fields;
    let accepted!: () => void;
    const committed = new Promise<void>((resolve) => {
      accepted = resolve;
    });
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route(
      `**${path}/review`,
      async (route) => {
        const response = await route.fetch();
        expect(response.status()).toBe(200);
        accepted();
        await held;
        await route.fulfill({ response });
      },
      { times: 1 },
    );
    const seller = page.locator('#field-seller_name');
    const saved = () =>
      expect(page.locator('.save-status')).toHaveText('Đã lưu nháp trên máy chủ.');
    await seller.fill('PDF edit A');
    await committed;
    await seller.fill('PDF edit AB');
    await expect(
      page.getByRole('button', { name: 'Xác nhận bản lưu', exact: true }),
    ).toBeDisabled();
    release();
    await saved();
    await expect(seller).toHaveValue('PDF edit AB');
    expect((await (await page.request.get(path)).json()).review.effective_data.seller_name).toBe(
      'PDF edit AB',
    );
    await seller.fill('');
    await saved();
    expect(
      (await (await page.request.get(path)).json()).review.effective_data.seller_name,
    ).toBeNull();
    await page.reload();
    await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
    await page.getByRole('button', { name: 'Mở tài liệu', exact: true }).click();
    await expect(seller).toHaveValue('');
    const session = await (await page.request.get('/api/v1/auth/session')).json();
    const current = await (await page.request.get(path)).json();
    const updated = await page.request.put(path + '/review', {
      headers: { Origin: baseURL, 'X-CSRF-Token': session.csrf_token },
      data: {
        run_id: doc.run.run_id,
        expected_revision: current.review.revision,
        expected_status: 'draft',
        fields: {
          seller_name: { is_reviewed: true, reviewed_value: 'Concurrent PDF server edit' },
        },
      },
    });
    expect(updated.status()).toBe(200);
    const conflictResponse = page.waitForResponse(
      (response) => response.url().endsWith(path + '/review') && response.status() === 409,
    );
    await seller.fill('PDF edit retained after conflict');
    await conflictResponse;
    await expect(page.getByRole('alert')).toContainText('REVISION_CONFLICT');
    await page.getByRole('button', { name: 'Đối chiếu bản mới' }).click();
    await expect(page.locator('.conflict-box')).toContainText('Concurrent PDF server edit');
    await page.getByRole('button', { name: 'Giữ chỉnh sửa, dùng revision mới' }).click();
    await saved();
    const kept = await (await page.request.get(path)).json();
    expect(kept.review.effective_data.seller_name).toBe('PDF edit retained after conflict');

    const serverValue = 'PDF server edit kept after discarding';
    const secondUpdate = await page.request.put(path + '/review', {
      headers: { Origin: baseURL, 'X-CSRF-Token': session.csrf_token },
      data: {
        run_id: doc.run.run_id,
        expected_revision: kept.review.revision,
        expected_status: 'draft',
        fields: { seller_name: { is_reviewed: true, reviewed_value: serverValue } },
      },
    });
    expect(secondUpdate.status()).toBe(200);
    const serverDraft = (await secondUpdate.json()).review;
    const discardConflict = page.waitForResponse(
      (response) => response.url().endsWith(path + '/review') && response.status() === 409,
    );
    await seller.fill('PDF local edit to discard');
    await discardConflict;
    await expect(page.getByRole('alert')).toContainText('REVISION_CONFLICT');
    await page.getByRole('button', { name: 'Đối chiếu bản mới' }).click();
    await expect(page.locator('.conflict-box')).toContainText(serverValue);
    await page.getByRole('button', { name: 'Bỏ chỉnh sửa, tải bản máy chủ' }).click();
    await expect(seller).toHaveValue(serverValue);
    expect((await (await page.request.get(path)).json()).review).toEqual(serverDraft);

    const visible = {
      invoice_number: '0041007',
      invoice_date: '2026-10-08',
      seller_name: 'PDF edit retained after conflict',
      total_amount: '1000000',
      currency: 'VND',
    };
    for (const [field, value] of Object.entries(visible))
      await page.locator(`#field-${field}`).fill(value);
    const review = page.getByRole('region', { name: 'Kiểm tra và sửa kết quả' });
    for (const checkbox of await review
      .getByRole('checkbox', { name: 'Đã đối chiếu trường này', exact: true })
      .all())
      await checkbox.check();
    await saved();
    await review.getByRole('button', { name: 'Xác nhận bản lưu', exact: true }).click();
    const downloadEvent = page.waitForEvent('download');
    await review.getByRole('button', { name: 'Xuất JSON đã xác nhận', exact: true }).click();
    const exported = JSON.parse(await readFile((await (await downloadEvent).path())!, 'utf8'));
    const confirmed = await (await page.request.get(path)).json();
    expect(confirmed.review.review_status).toBe('confirmed');
    expect(exported.data).toEqual({ ...visible, total_amount: 1000000 });
    expect(exported.data).toEqual(confirmed.review.effective_data);
    expect(exported.revision).toBe(confirmed.review.revision);
    expect(confirmed.run.fields).toEqual(prediction);
    const other = await foreign.newPage();
    await workspace(other);
    await login(other, 'pdfbeta');
    for (const suffix of [
      '',
      '/image',
      '/history',
      `/export?run_id=${doc.run.run_id}&revision=${exported.revision}`,
    ]) {
      expect((await other.request.get(path + suffix)).status()).toBe(404);
    }
    const revisionRequest = { run_id: doc.run.run_id, expected_revision: exported.revision };
    const withoutCSRF = await other.request.post(path + '/confirm', {
      headers: { Origin: baseURL },
      data: revisionRequest,
    });
    expect(withoutCSRF.status()).toBe(403);
    const otherSession = await (await other.request.get('/api/v1/auth/session')).json();
    const headers = { Origin: baseURL, 'X-CSRF-Token': otherSession.csrf_token };
    expect(
      (await other.request.post(path + '/confirm', { headers, data: revisionRequest })).status(),
    ).toBe(404);
    expect(
      (
        await other.request.put(path + '/review', {
          headers,
          data: { ...revisionRequest, expected_status: 'confirmed', fields: {} },
        })
      ).status(),
    ).toBe(404);
    expect((await (await page.request.get(path)).json()).review).toEqual(confirmed.review);
    expect((await (await other.request.get('/api/v1/documents')).json()).total).toBe(0);
  } finally {
    release?.();
    await owner.close();
    await foreign.close();
  }
});

test('PDF recovery: reload retains draft, cross-tab logout rejects late ACK in next account', async ({
  browser,
}) => {
  const context = await browser.newContext({ baseURL });
  let release!: () => void;
  try {
    const page = await context.newPage();
    await workspace(page);
    await login(page, 'pdfrecovery');
    const doc = await upload(page, 'pdf');
    const path = `/api/v1/documents/${doc.document_id}`;
    await page.route(`**${path}/review`, (route) => route.abort());
    await page.locator('#field-seller_name').fill('Recovered PDF draft');
    await expect(page.locator('.save-status')).toContainText('Lưu thất bại');
    await page.reload();
    await page.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
    await page.getByRole('button', { name: 'Mở tài liệu', exact: true }).click();
    await expect(page.locator('#field-seller_name')).toHaveValue('Recovered PDF draft');
    await expect(page.getByRole('alert')).toContainText('RECOVERED_DRAFT');
    expect((await (await page.request.get(path)).json()).review.effective_data.seller_name).toBe(
      doc.review.effective_data.seller_name,
    );
    await page.unroute(`**${path}/review`);
    let committed = false;
    let oldRequestAborted = false;
    let handled!: () => void;
    const settled = new Promise<void>((resolve) => {
      handled = resolve;
    });
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    page.on('requestfailed', (request) => {
      if (
        request.url().endsWith(path + '/review') &&
        request.failure()?.errorText.includes('ERR_ABORTED')
      )
        oldRequestAborted = true;
    });
    await page.route(
      `**${path}/review`,
      async (route) => {
        const response = await route.fetch();
        expect(response.status()).toBe(200);
        committed = true;
        await held;
        try {
          await route.fulfill({ response });
        } catch (error) {
          if (!oldRequestAborted) throw error;
        } finally {
          handled();
        }
      },
      { times: 1 },
    );
    await page.getByRole('button', { name: 'Đối chiếu bản mới' }).click();
    await page.getByRole('button', { name: 'Giữ chỉnh sửa, dùng revision mới' }).click();
    await page.getByRole('button', { name: 'Lưu nháp', exact: true }).click();
    await expect.poll(() => committed).toBe(true);
    const identity = await (await page.request.get('/api/v1/auth/session')).json();
    const prefix = `field-review:user:${identity.user.id}:`;
    const other = await context.newPage();
    await workspace(other);
    await other.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
    await expect.poll(() => oldRequestAborted).toBe(true);
    await login(other, 'pdfnext');
    await expect(page.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText('pdfnext');
    const own = await upload(page, 'pdf');
    expect(own.document_id).not.toBe(doc.document_id);
    await page.route(`**/api/v1/documents/${own.document_id}/review`, (route) => route.abort());
    await page.locator('#field-seller_name').fill('Next account PDF draft');
    await expect(page.locator('.save-status')).toContainText('Lưu thất bại');
    release();
    // The server committed, but the old editor canceled delivery of its ACK.
    await settled;
    await expect(page.locator('#field-seller_name')).toHaveValue('Next account PDF draft');
    const storage = await page.evaluate(
      (prefix) => ({
        oldKeys: Object.keys(localStorage).filter((key) => key.startsWith(prefix)),
        drafts: Object.keys(localStorage)
          .filter((key) => key.startsWith('field-review:'))
          .map((key) => localStorage.getItem(key))
          .join('\n'),
      }),
      prefix,
    );
    expect(storage.oldKeys).toEqual([]);
    expect(storage.drafts).toContain('Next account PDF draft');
    expect(storage.drafts).not.toContain('Recovered PDF draft');
    expect((await page.request.get(path)).status()).toBe(404);
  } finally {
    release?.();
    await context.close();
  }
});
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
async function upload(page: Page, format: 'png' | 'pdf' = 'png') {
  await page
    .getByLabel('PNG/JPG/PDF một trang')
    .setInputFiles(
      format === 'pdf'
        ? fileURLToPath(
            new URL('../../pipeline/tests/fixtures/pdf/hoa_don_007.pdf', import.meta.url),
          )
        : image,
    );
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

test('focus refresh during pending login preserves the successful authenticated UI', async ({
  page,
}) => {
  await workspace(page);
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
  let releaseLogin!: () => void;
  let loginStarted!: () => void;
  const held = new Promise<void>((resolve) => {
    releaseLogin = resolve;
  });
  const started = new Promise<void>((resolve) => {
    loginStarted = resolve;
  });
  await page.route('**/api/v1/auth/login', async (route) => {
    loginStarted();
    await held;
    await route.continue();
  });
  await page.getByLabel('Tên đăng nhập').fill('alpha');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('synthetic-browser-password-123');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await started;
  const observed = page.waitForResponse('**/api/v1/auth/session');
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  expect((await (await observed).json()).user).toBeNull();
  const loggedIn = page.waitForResponse('**/api/v1/auth/login');
  releaseLogin();
  expect((await loggedIn).status()).toBe(200);
  expect((await (await page.request.get('/api/v1/auth/session')).json()).user.username).toBe(
    'alpha',
  );
  await expect(page.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText('alpha', {
    timeout: 3000,
  });
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toHaveCount(0);
});

test('owner recovery survives reload and is cleared by logout in another tab', async ({
  browser,
}) => {
  const context = await browser.newContext({ baseURL });
  try {
    const first = await context.newPage();
    await workspace(first);
    await login(first, 'epsilon');
    const doc = await upload(first);
    const session = await (await first.request.get('/api/v1/auth/session')).json();
    const prefix = `field-review:user:${session.user.id}:`;
    await first.route('**/api/v1/documents/*/review', (route) => route.abort());
    await first.locator('#field-seller_name').fill('Private epsilon recovery');
    await expect(first.locator('.save-status')).toContainText('Lưu thất bại');
    expect(
      await first.evaluate(
        (prefix) => Object.keys(localStorage).some((key) => key.startsWith(prefix)),
        prefix,
      ),
    ).toBe(true);
    await first.reload();
    await first.getByRole('button', { name: 'Xử lý tài liệu', exact: true }).click();
    await first.getByRole('button', { name: 'Mở tài liệu', exact: true }).click();
    await expect(first.locator('#field-seller_name')).toHaveValue('Private epsilon recovery');
    await expect(first.getByRole('alert')).toContainText('RECOVERED_DRAFT');
    const persisted = await (
      await first.request.get(`/api/v1/documents/${doc.document_id}`)
    ).json();
    expect(persisted.review.effective_data.seller_name).toBe(doc.review.effective_data.seller_name);
    const second = await context.newPage();
    await workspace(second);
    await second.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
    await expect(first.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
    expect(
      await first.evaluate(
        (prefix) => Object.keys(localStorage).some((key) => key.startsWith(prefix)),
        prefix,
      ),
    ).toBe(false);
    await login(second, 'zeta');
    await expect(first.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText('zeta');
    await first.unroute('**/api/v1/documents/*/review');
    await upload(first);
    await expect(first.locator('#field-seller_name')).not.toHaveValue('Private epsilon recovery');
    await expect(first.getByRole('alert').filter({ hasText: 'RECOVERED_DRAFT' })).toHaveCount(0);
  } finally {
    await context.close();
  }
});

test('revoked session clears a pending owner draft and a late successful ACK cannot alter the next account', async ({
  browser,
}) => {
  const context = await browser.newContext({ baseURL });
  let release!: () => void;
  try {
    const page = await context.newPage();
    await workspace(page);
    await login(page, 'eta');
    const doc = await upload(page);
    const session = await (await page.request.get('/api/v1/auth/session')).json();
    const oldPrefix = `field-review:user:${session.user.id}:`;
    let saved!: () => void;
    let handled!: () => void;
    let oldRequestAborted = false;
    const oldPath = `/documents/${doc.document_id}/review`;
    page.on('requestfailed', (request) => {
      if (request.url().endsWith(oldPath) && request.failure()?.errorText.includes('ERR_ABORTED'))
        oldRequestAborted = true;
    });
    const oldHandled = new Promise<void>((resolve) => {
      handled = resolve;
    });
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const accepted = new Promise<void>((resolve) => {
      saved = resolve;
    });
    await page.route(`**/api/v1/documents/${doc.document_id}/review`, async (route) => {
      const response = await route.fetch();
      expect(response.status()).toBe(200);
      saved();
      await gate;
      try {
        await route.fulfill({ response });
      } catch (error) {
        if (!oldRequestAborted) throw error;
      } finally {
        handled();
      }
    });
    await page.locator('#field-seller_name').fill('Old eta acknowledged draft');
    await accepted;
    expect(
      (
        await page.request.post('/api/v1/auth/logout', {
          headers: { 'X-CSRF-Token': session.csrf_token, Origin: baseURL },
        })
      ).status(),
    ).toBe(204);
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
    await expect.poll(() => oldRequestAborted).toBe(true);
    expect(
      await page.evaluate(
        (prefix) => Object.keys(localStorage).some((key) => key.startsWith(prefix)),
        oldPrefix,
      ),
    ).toBe(false);
    await login(page, 'theta');
    const own = await upload(page);
    await page.route(`**/api/v1/documents/${own.document_id}/review`, (route) => route.abort());
    await page.locator('#field-seller_name').fill('Theta pending recovery');
    await expect(page.locator('.save-status')).toContainText('Lưu thất bại');
    release();
    // The server's 200 was asserted above. The editor lifecycle canceled its
    // client request, so a response event must not be required after revocation.
    await oldHandled;
    await expect(page.getByRole('region', { name: 'Tài khoản hiện tại' })).toContainText('theta');
    await expect(page.locator('#field-seller_name')).toHaveValue('Theta pending recovery');
    expect(
      await page.evaluate(
        (prefix) => Object.keys(localStorage).some((key) => key.startsWith(prefix)),
        oldPrefix,
      ),
    ).toBe(false);
    const stored = await page.evaluate(() =>
      Object.keys(localStorage)
        .filter((key) => key.startsWith('field-review:'))
        .map((key) => localStorage.getItem(key))
        .join('\n'),
    );
    expect(stored).toContain('Theta pending recovery');
    expect(stored).not.toContain('Old eta acknowledged draft');
  } finally {
    release?.();
    await context.close();
  }
});

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
