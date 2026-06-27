import { test, expect } from '@playwright/test'

test.describe('Home Page', () => {
  test('should display the hero section', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1').first()).toBeVisible()
    await expect(page.locator('text=Smart Tire Analyzer')).toBeVisible()
  })

  test('should navigate to analyze page', async ({ page }) => {
    await page.goto('/')
    await page.locator('a[href="/analyze"]').first().click()
    await expect(page).toHaveURL(/\/analyze/)
  })

  test('should navigate to login page', async ({ page }) => {
    await page.goto('/')
    await page.locator('a[href="/login"]').first().click()
    await expect(page).toHaveURL(/\/login/)
  })
})
