import { expect, test } from '@playwright/test'

test('applies saved theme before React starts and retains it after reload', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await page.addInitScript(() => localStorage.setItem('ai02-solo-theme-v1', 'dark'))
  await page.route('**/src/main.tsx', route => route.abort())
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute('content', '#161c1a')
  await page.unroute('**/src/main.tsx')
  await page.reload()
  await page.getByRole('button', { name: 'Chuyển sang chế độ sáng' }).click()
  // The init script above represents the saved value on the first visit only.
  // A fresh page in the same context must read the actual updated localStorage.
  const next = await page.context().newPage()
  await next.goto('/')
  await expect(next.locator('html')).toHaveAttribute('data-theme', 'light')
  await next.reload()
  await expect(next.locator('html')).toHaveAttribute('data-theme', 'light')
  await next.close()
})

test('theme switching preserves reviewed values and validation across desktop and mobile', async ({ page }, testInfo) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/')
  await page.getByRole('button', { name: /Dùng hóa đơn mẫu/ }).click()
  await page.getByRole('button', { name: /Trích xuất dữ liệu/ }).click()
  const seller = page.locator('#seller_name')
  await expect(seller).toBeVisible()
  await seller.fill('Cửa hàng Thử giao diện')
  await page.getByRole('button', { name: 'Kiểm tra dữ liệu' }).click()
  const exportButton = page.getByRole('button', { name: /Xuất JSON/ })
  await expect(exportButton).toBeEnabled()
  for (const theme of ['light', 'dark']) {
    await page.getByRole('button', { name: `Chuyển sang chế độ ${theme === 'light' ? 'sáng' : 'tối'}` }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
    await expect(page.locator('html')).toHaveCSS('background-color', theme === 'light' ? 'rgb(243, 245, 239)' : 'rgb(22, 28, 26)')
    await expect(seller).toHaveValue('Cửa hàng Thử giao diện')
    await expect(exportButton).toBeEnabled()
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await page.evaluate(() => window.scrollTo(0, 0))
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await expect(page.getByRole('button', { name: /Chuyển sang chế độ/ })).toBeVisible()
      await page.screenshot({ path: testInfo.outputPath(`${theme}-${width}.png`), fullPage: true, animations: 'disabled' })
    }
  }
})
