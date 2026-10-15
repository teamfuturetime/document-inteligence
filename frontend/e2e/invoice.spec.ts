import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../..', import.meta.url))
const samples = path.join(root, 'data/samples')

for (const extension of ['png', 'jpg', 'pdf']) {
  test(`${extension}: real upload, edit, validate and download contract JSON`, async ({ page, request }, testInfo) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    expect((await (await request.get('/health')).json()).ocr_ready).toBe(true)
    await page.goto('/')
    await page.getByLabel('Chọn PNG, JPG hoặc PDF').setInputFiles(path.join(samples, `synthetic-001.${extension}`))
    if (extension === 'pdf') await expect(page.getByLabel('Xem trước PDF')).toBeVisible()
    else await expect(page.getByAltText(`Xem trước synthetic-001.${extension}`)).toHaveJSProperty('naturalWidth', 1200)
    await page.getByRole('button', { name: 'Trích xuất hóa đơn' }).click()
    await expect(page.getByLabel('Số hóa đơn', { exact: true })).toHaveValue('SYN-0001')
    await expect(page.getByText('Kết quả mock — chưa chạy OCR')).toHaveCount(0)
    await page.getByLabel('Ngày hóa đơn', { exact: true }).fill('2026-02-30')
    await page.getByRole('button', { name: 'Kiểm tra dữ liệu', exact: true }).click()
    await expect(page.getByLabel('Ngày hóa đơn', { exact: true })).toHaveAttribute('aria-invalid', 'true')
    await page.getByLabel('Ngày hóa đơn', { exact: true }).fill('2026-10-09')
    await page.getByLabel('Bên bán', { exact: true }).fill('Cửa hàng đã review')
    const exportButton = page.getByRole('button', { name: 'Xuất JSON đã xác nhận' })
    await expect(exportButton).toBeDisabled()
    await page.getByRole('button', { name: 'Kiểm tra dữ liệu', exact: true }).click()
    await expect(exportButton).toBeEnabled()
    const downloadEvent = page.waitForEvent('download')
    await exportButton.click()
    const download = await downloadEvent
    const filename = await download.path()
    const raw = await readFile(filename!, 'utf-8')
    const output = JSON.parse(raw)
    expect(output.values.seller_name).toBe('Cửa hàng đã review')
    expect(output.original_extraction.mode).toBe('real')
    expect(output.original_extraction.fields.seller_name.value).toBe('Cửa hàng Mây Việt - dữ liệu giả')
    expect(output.edited_fields).toEqual(['seller_name'])
    execFileSync(path.join(root, '.venv/bin/python'), ['-c',
      'import sys; from document_contracts.models import ReviewedExport; ReviewedExport.model_validate_json(sys.stdin.read())'],
      { input: raw, cwd: root })
    if (extension === 'png') await page.locator('.review').screenshot({ path: testInfo.outputPath('review.png') })
    await page.getByLabel('Tổng tiền', { exact: true }).fill('1')
    await expect(exportButton).toBeDisabled()
    expect(errors).toEqual([])
  })
}

test('missing currency blocks export until supplied by reviewer', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Chọn PNG, JPG hoặc PDF').setInputFiles(path.join(samples, 'synthetic-002-missing.png'))
  await page.getByRole('button', { name: 'Trích xuất hóa đơn' }).click()
  await expect(page.getByLabel('Số hóa đơn', { exact: true })).toHaveValue('SYN-0002')
  await expect(page.getByLabel('Tiền tệ', { exact: true })).toHaveValue('')
  await page.getByRole('button', { name: 'Kiểm tra dữ liệu', exact: true }).click()
  await expect(page.getByLabel('Tiền tệ', { exact: true })).toHaveAttribute('aria-invalid', 'true')
  await expect(page.getByRole('button', { name: 'Xuất JSON đã xác nhận' })).toBeDisabled()
  await page.getByLabel('Tiền tệ', { exact: true }).fill('VND')
  await page.getByRole('button', { name: 'Kiểm tra dữ liệu', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Xuất JSON đã xác nhận' })).toBeEnabled()
})

test('corrupt content gets a visible API error and cannot export', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Chọn PNG, JPG hoặc PDF').setInputFiles({ name: 'broken.png', mimeType: 'image/png', buffer: Buffer.from('not an image') })
  await page.getByRole('button', { name: 'Trích xuất hóa đơn' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Xuất JSON đã xác nhận' })).toHaveCount(0)
})

test('oversized files are rejected before upload', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Chọn PNG, JPG hoặc PDF').setInputFiles({ name: 'large.png', mimeType: 'image/png', buffer: Buffer.alloc(10 * 1024 * 1024 + 1) })
  await expect(page.getByRole('alert')).toContainText('10 MiB')
  await expect(page.getByRole('button', { name: 'Trích xuất hóa đơn' })).toHaveCount(0)
})

test('mobile layout fits viewport and image preview renders', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByLabel('Chọn PNG, JPG hoặc PDF').setInputFiles(path.join(samples, 'synthetic-001.png'))
  await expect(page.getByAltText('Xem trước synthetic-001.png')).toHaveJSProperty('naturalWidth', 1200)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true })
})
