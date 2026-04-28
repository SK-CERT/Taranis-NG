import { test, expect } from '@playwright/test'
import { login, logout, waitForNotification } from '../helpers/test-helpers'

/**
 * Authentication E2E Tests
 *
 * Tests login, logout, and authentication flows
 */

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Start each test from login page
    await page.goto('/v2/login')
  })

  test('should display login page', async ({ page }) => {
    // Verify login page elements
    await expect(page).toHaveTitle(/Taranis/i)
    await expect(page.locator('[data-test="login-username"] input')).toBeVisible()
    await expect(page.locator('[data-test="login-password"] input')).toBeVisible()
    await expect(page.locator('[data-test="login-submit"]')).toBeVisible()
  })

  test('should login with valid credentials', async ({ page }) => {
    // Fill login form
    await page.locator('[data-test="login-username"] input').fill('admin')
    await page.locator('[data-test="login-password"] input').fill('admin')

    // Submit form
    await page.locator('[data-test="login-submit"]').click()

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/v2\/(dashboard)?$/)

    // Should show user info or dashboard content
    await expect(page.locator('text=Dashboard')).toBeVisible()
  })

  test('should show error with invalid credentials', async ({ page }) => {
    // Fill with invalid credentials
    await page.locator('[data-test="login-username"] input').fill('invalid')
    await page.locator('[data-test="login-password"] input').fill('wrong')

    // Submit form
    await page.locator('[data-test="login-submit"]').click()

    // Should show inline login error
    await expect(page.locator('[data-test="login-error"]')).toBeVisible()

    // Should remain on login page
    await expect(page).toHaveURL(/login/)
  })

  test('should show error with empty credentials', async ({ page }) => {
    // Submit without filling
    await page.locator('[data-test="login-submit"]').click()

    // Should show validation errors from vee-validate
    await expect(page.locator('text=Please fill in your username')).toBeVisible()
    await expect(page.locator('text=Password is required')).toBeVisible()
  })

  test('should logout successfully', async ({ page }) => {
    // Login first
    await login(page)

    // Verify logged in
    await expect(page).toHaveURL('/v2/')

    // Logout
    await logout(page)

    // Should redirect to login page
    await expect(page).toHaveURL('/v2/login')
  })

  test('should redirect to login when accessing protected route without auth', async ({ page, context }) => {
    // Clear any existing auth
    await context.clearCookies()

    // Try to access protected route
    await page.goto('/v2/config/roles')

    // Should redirect to login
    await expect(page).toHaveURL(/login/)
  })

  test('should persist session after page reload', async ({ page }) => {
    // Login
    await login(page)

    // Reload page
    await page.reload()

    // Should still be logged in
    await expect(page).toHaveURL(/\/v2\/(dashboard)?$/)
    await expect(page.locator('text=Dashboard')).toBeVisible()
  })
})
