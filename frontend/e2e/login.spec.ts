import { test, expect } from '@playwright/test'

test.describe('Login Page', () => {
  test('should display the login form', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('text=Email')).toBeVisible()
    await expect(page.locator('text=Password')).toBeVisible()
    await expect(page.locator('button:has-text("Sign In")')).toBeVisible()
  })

  test('should show validation errors for empty fields', async ({ page }) => {
    await page.goto('/login')
    await page.locator('button:has-text("Sign In")').click()
    // Form should show validation
    await expect(page.locator('text=required')).toBeVisible()
  })
})
