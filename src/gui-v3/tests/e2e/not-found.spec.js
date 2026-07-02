import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'

/**
 * 404 / Not Found E2E Tests
 *
 * Unknown paths — both under /config and at the top level — should render the
 * NotFound view (catch-all route) instead of a blank page, and offer a way back.
 */

test.describe('Not Found (404)', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('shows a 404 page for an unknown /config path', async ({ page }) => {
        await page.goto('/v2/config/this-does-not-exist')

        await expect(page.getByText('Page not found')).toBeVisible()
        // The attempted path is echoed back to the user.
        await expect(page.getByText('/config/this-does-not-exist')).toBeVisible()
    })

    test('shows a 404 page for an unknown top-level path', async ({ page }) => {
        await page.goto('/v2/totally-unknown-page')

        await expect(page.getByText('Page not found')).toBeVisible()
        await expect(page.getByText('/totally-unknown-page')).toBeVisible()
    })

    test('"Go to home" navigates away from the unknown path', async ({ page }) => {
        await page.goto('/v2/nope-nope-nope')
        await expect(page.getByText('Page not found')).toBeVisible()

        await page.getByRole('button', { name: 'Go to home' }).click()

        // Root resolves to the user's default landing page (dashboard/config), never the bad path.
        await expect(page).not.toHaveURL(/nope-nope-nope/)
        await expect(page).toHaveURL(/\/v2\/(dashboard|config|assess)/)
    })
})
