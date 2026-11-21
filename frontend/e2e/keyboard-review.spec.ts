import { expect, test, type Locator, type Page } from '@playwright/test';
import type { DocumentDetail } from '../src/features/documents/api';

async function tabTo(page: Page, target: Locator) {
  for (let i = 0; i < 90; i++) {
    if (await target.evaluate((element) => element === document.activeElement)) return;
    await page.keyboard.press('Tab');
  }
  throw new Error('Target was not reachable by Tab');
}

for (const width of [1280, 390]) {
  test(`keyboard review, null, recovery, conflict and confirmed export at ${width}px (HTTP doubles)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 850 });
    let current: DocumentDetail = {
      document_id: 'keyboard',
      document_type: 'hoa_don',
      filename: 'synthetic-keyboard.png',
      data_origin: 'synthetic',
      input_sha256: 'a'.repeat(64),
      image_width: 100,
      image_height: 100,
      created_at: '2026-11-20T00:00:00Z',
      latest_run_id: 'run',
      status: 'succeeded',
      image_url: '/keyboard-image',
      is_latest_run: true,
      definitions: [
        { field_id: 'seller_name', label: 'Đơn vị bán hàng', value_type: 'text', required: true },
      ],
      run: {
        run_id: 'run',
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
        effective_data: { seller_name: 'Synthetic seller' },
        validation_issues: [],
      },
    };
    let failure = 0;
    let holdSave = false;
    let finishSave: (() => void) | undefined;
    let nullSaved = false;
    let writes = 0;
    await page.route('**/keyboard-image?*', (route) =>
      route.fulfill({
        contentType: 'image/svg+xml',
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"/>',
      }),
    );
    await page.route('**/api/v1/**', async (route) => {
      const path = new URL(route.request().url()).pathname;
      let value: unknown = current;
      if (path.endsWith('/auth/session')) value = { mode: 'local', user: null, csrf_token: null };
      else if (path.endsWith('/capabilities'))
        value = {
          features: {},
          max_upload_bytes: 5242880,
          model_benchmark_status: 'not_measured',
          ocr_ready: true,
          provider_mode: 'tesseract',
          supported_schemas: [],
        };
      else if (path.endsWith('/document-schemas')) value = [];
      else if (path.endsWith('/insights')) value = { documents: 1 };
      else if (path.endsWith('/history')) value = { runs: [], events: [] };
      else if (path.endsWith('/documents'))
        value = { items: [current], total: 1, offset: 0, limit: 10 };
      else if (path.endsWith('/review')) {
        writes++;
        const body = route.request().postDataJSON();
        expect(body.run_id).toBe('run');
        expect(body.expected_revision).toBe(current.review!.revision);
        expect(body.expected_status).toBe('draft');
        if (failure) {
          const status = failure;
          failure = 0;
          return route.fulfill({
            status,
            json: {
              error: {
                code: status === 409 ? 'REVISION_CONFLICT' : 'SAVE_FAILED',
                message: 'Giữ chỉnh sửa để đối chiếu.',
              },
            },
          });
        }
        if (holdSave) {
          holdSave = false;
          await new Promise<void>((resolve) => (finishSave = resolve));
        }
        const field = body.fields.seller_name;
        nullSaved ||= field.is_reviewed && field.reviewed_value === null;
        current = {
          ...current,
          review: {
            ...current.review!,
            revision: current.review!.revision + 1,
            fields: body.fields,
            effective_data: { seller_name: field.reviewed_value },
            validation_issues:
              field.reviewed_value === null
                ? [
                    {
                      field_path: 'seller_name',
                      code: 'REQUIRED',
                      message: 'Cần đơn vị bán hàng',
                      severity: 'error',
                    },
                  ]
                : [],
          },
        };
        value = current;
      } else if (path.endsWith('/confirm')) {
        expect(route.request().postDataJSON()).toEqual({
          run_id: 'run',
          expected_revision: current.review!.revision,
        });
        expect(current.review!.validation_issues).toHaveLength(0);
        current = { ...current, review: { ...current.review!, review_status: 'confirmed' } };
        value = current;
      } else if (path.endsWith('/export')) {
        const query = new URL(route.request().url()).searchParams;
        expect(query.get('run_id')).toBe('run');
        expect(query.get('revision')).toBe(String(current.review!.revision));
        expect(current.review!.review_status).toBe('confirmed');
        value = {
          run_id: 'run',
          revision: current.review!.revision,
          data: current.review!.effective_data,
        };
      }
      await route.fulfill({ json: value });
    });
    const button = (name: string) => page.getByRole('button', { name, exact: true });
    const input = page.getByRole('textbox', { name: 'Đơn vị bán hàng *' });
    async function activate(name: string, key = 'Enter') {
      await tabTo(page, button(name));
      await page.keyboard.press(key);
    }
    async function open() {
      await activate('Xử lý tài liệu');
      await activate('Mở tài liệu');
    }
    await page.goto('/');
    await open();
    await expect(page.getByRole('heading', { name: 'Kiểm tra dữ liệu' })).toBeFocused();
    await tabTo(page, input);
    await page.keyboard.press('ControlOrMeta+A');
    await page.keyboard.press('Backspace');
    await expect(page.getByRole('status', { name: 'Trạng thái lưu' })).toContainText('Đã lưu nháp');
    expect(nullSaved).toBe(true);
    await expect(page.getByRole('status', { name: 'Kiểm tra tính hợp lệ' })).toContainText(
      '1 trường',
    );
    await expect(button('Xác nhận bản lưu')).toBeDisabled();
    failure = 409;
    await page.keyboard.insertText('Local edits');
    await expect(page.getByRole('alert', { name: 'Lỗi lưu bản rà soát' })).toContainText(
      'REVISION_CONFLICT',
    );
    await expect(input).toBeFocused();
    const beforeCompare = writes;
    await activate('Đối chiếu bản mới');
    await expect(
      page.getByRole('region', { name: 'Đối chiếu chỉnh sửa với máy chủ' }),
    ).toBeFocused();
    expect(writes).toBe(beforeCompare);
    await activate('Giữ chỉnh sửa, dùng revision mới', 'Space');
    await expect(input).toBeFocused();
    await expect(input).toHaveValue('Local edits');
    await expect(page.getByRole('status', { name: 'Trạng thái lưu' })).toContainText('Đã lưu nháp');
    failure = 500;
    await page.keyboard.press('ControlOrMeta+A');
    await page.keyboard.insertText('Recovered pending');
    await expect(page.getByRole('alert')).toContainText('SAVE_FAILED');
    await activate('Lưu nháp', 'Space');
    await expect(input).toBeFocused();
    await expect(page.getByRole('status', { name: 'Trạng thái lưu' })).toContainText('Đã lưu nháp');
    failure = 500;
    await page.keyboard.insertText(' pending');
    await expect(page.getByRole('alert')).toContainText('SAVE_FAILED');
    holdSave = true;
    await activate('Lưu nháp');
    await expect.poll(() => !!finishSave).toBe(true);
    const source = button('Xem vùng nguồn: Đơn vị bán hàng');
    await tabTo(page, source);
    finishSave!();
    await expect(page.getByRole('status', { name: 'Trạng thái lưu' })).toContainText('Đã lưu nháp');
    await expect(source).toBeFocused();
    await tabTo(page, input);
    failure = 500;
    await page.keyboard.press('ControlOrMeta+A');
    await page.keyboard.insertText('Unsaved after focus move');
    await expect(page.getByRole('alert')).toContainText('SAVE_FAILED');
    await page.reload();
    await open();
    await expect(page.getByRole('alert', { name: 'Lỗi lưu bản rà soát' })).toBeFocused();
    await expect(input).toHaveValue('Unsaved after focus move');
    await activate('Đối chiếu bản mới');
    await activate('Bỏ chỉnh sửa, tải bản máy chủ', 'Space');
    await expect(input).toBeFocused();
    await expect(input).toHaveValue('Recovered pending pending');
    await activate('Xác nhận bản lưu');
    await expect(button('Xuất JSON đã xác nhận')).toBeFocused();
    const downloadEvent = page.waitForEvent('download');
    await page.keyboard.press('Space');
    const stream = await (await downloadEvent).createReadStream();
    let json = '';
    for await (const chunk of stream!) json += chunk.toString();
    expect(JSON.parse(json).data.seller_name).toBe('Recovered pending pending');
    await page.keyboard.press('Tab');
    await expect(button('Xuất JSON đã xác nhận')).not.toBeFocused();
    await expect(
      page.getByRole('img', { name: 'Bằng chứng OCR: Đơn vị bán hàng' }),
    ).toHaveAccessibleDescription(/chưa có bằng chứng/);
  });
}
