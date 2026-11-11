// Opt-in live check. Exactly one OCR.space request using a committed synthetic image.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

if (process.env.SOLO_RUN_OCRSPACE !== '1') {
  throw new Error('Set SOLO_RUN_OCRSPACE=1 to authorize one live synthetic OCR.space request. Start the local app first.')
}
const web = fileURLToPath(new URL('..', import.meta.url))
const output = path.join(web, 'test-results')
const browser = await chromium.launch({ executablePath: process.env.SOLO_BROWSER_PATH || undefined })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true })
  let browserCredential = false
  page.on('request', request => {
    if (request.url().startsWith('https://api.ocr.space') || 'apikey' in request.headers()) browserCredential = true
  })
  await page.goto(process.env.SOLO_BASE_URL || 'http://127.0.0.1:5174/')
  // Auto-wait for health/settings before selecting: late defaults must not reset this choice.
  await page.getByLabel('Nguồn OCR').selectOption('ocrspace')
  await page.getByLabel('Loại tài liệu').selectOption('invoice')
  await page.getByLabel('Phương pháp').selectOption('rules')
  await page.getByLabel('Tải tài liệu mẫu').setInputFiles(path.join(web, '../data/golden-v1/invoice-001.png'))
  const pending = page.waitForResponse(response => response.url().endsWith('/api/extract'), { timeout: 90000 })
  await page.getByRole('button', { name: /Trích xuất dữ liệu/ }).click()
  const response = await pending
  assert.equal(response.status(), 200, 'Cloud extraction did not succeed')
  const result = await response.json()
  assert.equal(result.provenance.ocr.provider, 'ocrspace')
  const truth = JSON.parse(fs.readFileSync(path.join(web, '../data/golden-v1/invoice-001.json'), 'utf8'))
  assert.deepEqual(Object.fromEntries(Object.entries(result.fields).map(([key, field]) => [key, field.value])), truth)
  assert(Object.values(result.fields).every(field => field.confidence === null))
  await page.locator('#seller_name').fill('Cửa hàng Mẫu đã kiểm tra')
  await page.getByRole('button', { name: 'Kiểm tra dữ liệu' }).click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /Xuất JSON/ }).click()
  const download = await downloadPromise
  const exported = JSON.parse(fs.readFileSync(await download.path(), 'utf8'))
  assert.equal(exported.original_extraction.provenance.ocr.provider, 'ocrspace')
  assert.deepEqual(exported.edited_fields, ['seller_name'])
  assert.equal(browserCredential, false, 'API key must stay on the backend')
  fs.mkdirSync(output, { recursive: true })
  await page.screenshot({ path: path.join(output, 'ocrspace-live-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await page.screenshot({ path: path.join(output, 'ocrspace-live-mobile.png'), fullPage: true })
  const summary = { live_cloud_ui: true, provider: 'ocrspace', engine: result.provenance.ocr.engine,
    correct_fields: 5, confidence_null: true, review_download: true, browser_has_no_api_key: true, mobile_fits: true }
  fs.writeFileSync(path.join(output, 'ocrspace-live-summary.json'), JSON.stringify(summary, null, 2) + '\n')
  console.log(JSON.stringify(summary))
} finally {
  await browser.close()
}
