import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const data = fileURLToPath(new URL('../../data/golden-v1/', import.meta.url))
const manifest = JSON.parse(fs.readFileSync(path.join(data, 'manifest.json'), 'utf8'))

for (const kind of ['invoice', 'application']) {
  for (const index of ['001', '002', '003']) {
    test(`${kind} ${index}: real OCR, review, validation and downloaded JSON`, async ({ page }, testInfo) => {
      const item = manifest.documents.find((item: { id: string }) => item.id === `${kind}-${index}`)
      const truth = JSON.parse(fs.readFileSync(path.join(data, item.truth), 'utf8'))
      await page.goto('/')
      await page.getByLabel('Loại tài liệu').selectOption(kind)
      await page.getByLabel('Tải tài liệu mẫu').setInputFiles(path.join(data, item.file))
      const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/extract'))
      await page.getByRole('button', { name: /Trích xuất dữ liệu/ }).click()
      const response = await responsePromise
      expect(response.status()).toBe(200)
      const original = await response.json()
      const id = kind === 'invoice' ? 'invoice_number' : 'student_id'
      expect(original.fields[id].value).toBe(truth[id])
      const expected: Record<string, string | number> = {}
      for (const [key, value] of Object.entries(truth)) {
        const final = value ?? (key === 'currency' ? 'VND' : 'Xin xác nhận dữ liệu tổng hợp')
        expected[key] = final as string | number
        await page.locator(`#${key}`).fill(String(final))
      }
      const edit = kind === 'invoice' ? 'seller_name' : 'applicant_name'
      expected[edit] = 'Đơn vị Mẫu Đã Rà Soát'
      await page.locator(`#${edit}`).fill(String(expected[edit]))
      await expect(page.getByRole('button', { name: /Xuất JSON/ })).toBeDisabled()
      await page.getByRole('button', { name: 'Kiểm tra dữ liệu' }).click()
      await expect(page.getByRole('button', { name: /Xuất JSON/ })).toBeEnabled()
      const downloadPromise = page.waitForEvent('download')
      await page.getByRole('button', { name: /Xuất JSON/ }).click()
      const download = await downloadPromise
      const output = await download.path()
      const exported = JSON.parse(fs.readFileSync(output!, 'utf8'))
      expect(exported.values).toEqual(expected)
      expect(exported.original_extraction).toEqual(original)
      expect(exported.edited_fields.sort()).toEqual(Object.keys(expected).filter(key => expected[key] !== original.fields[key].value).sort())
      if (kind === 'invoice' && index === '001') await page.screenshot({ path: testInfo.outputPath('desktop.png'), fullPage: true })
    })
  }
}

test('mobile preview fits viewport and corrupt upload shows an error', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByLabel('Tải tài liệu mẫu').setInputFiles(path.join(data, 'invoice-001.png'))
  await expect(page.getByAltText('Bản xem trước invoice-001.png')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true })
  await page.getByLabel('Tải tài liệu mẫu').setInputFiles({ name: 'corrupt.png', mimeType: 'image/png', buffer: Buffer.from('not-a-document') })
  await page.getByRole('button', { name: /Trích xuất dữ liệu/ }).click()
  await expect(page.getByRole('alert')).toContainText('Không đọc được')
})
