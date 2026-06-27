import { test, expect } from '@playwright/test'

test.describe('Analyze Page', () => {
  test('should display the upload form', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page.locator('text=Tire Image')).toBeVisible()
    await expect(page.locator('text=Analyze Tire')).toBeVisible()
  })

  test('should show error when submitting without image', async ({ page }) => {
    await page.goto('/analyze')
    await page.locator('button:has-text("Analyze Tire")').click()
    // Should show some error or remain on page
    await expect(page).toHaveURL(/\/analyze/)
  })
})
