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

    test('should reach the login page without a rejected redemption', async ({ page }) => {
        // The login page POSTs /auth/redeem on every mount: the one-time handle left by an
        // OIDC/SAML round trip is HttpOnly, so the GUI cannot tell whether one exists and
        // has to ask. Anything but a clean answer surfaces as a failed request in the
        // console and a login-error banner on an otherwise ordinary visit. This runs in the
        // dev-server setup Playwright boots (see playwright.config.js), where the GUI is on
        // :4444 and core on another port - a cross-origin call that core accepts only
        // because TARANIS_NG_CORS_ORIGINS in docker/.env.e2e grants that origin.
        // Armed before navigating and awaited after: the POST is only issued once
        // /auth/methods resolves, which is also what renders the form, so waiting on
        // the form and then reading collected responses races the request. The wait
        // times out if the call never happens, which is the other half of the check.
        const redemption = page.waitForResponse('**/api/v1/auth/redeem')

        await page.goto('/v2/login')

        // 204 is the normal "nothing to redeem"; 200 carries a verdict to apply.
        expect((await redemption).status()).toBeLessThan(400)
        await expect(page.locator('[data-test="login-submit"]')).toBeVisible()
        await expect(page.locator('[data-test="login-error"]')).toBeHidden()
    })

    test('should login with valid credentials', async ({ page }) => {
        // Fill login form
        await page.locator('[data-test="login-username"] input').fill('admin')
        await page.locator('[data-test="login-password"] input').fill('admin')

        // Submit form
        await page.locator('[data-test="login-submit"]').click()

        // Should redirect to dashboard
        await expect(page).toHaveURL(/\/v2\/(dashboard)?$/)

        // Assert on the dashboard's own heading. A bare `text=Dashboard` also matches the
        // primary-navigation link of the same name — two elements, strict-mode violation.
        await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
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

        // Verify logged in (router currently lands on dashboard)
        await expect(page).toHaveURL(/\/v2\/(dashboard)?$/)

        // Logout
        await logout(page)

        // Should redirect to login page
        await expect(page).toHaveURL('/v2/login')
    })

    test('should redirect to login when accessing protected route without auth', async ({ page, context }) => {
        // Clear any existing auth
        await context.clearCookies()

        // Try to access protected route
        await page.goto('/v2/config/access-management')

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
        await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    })
})
