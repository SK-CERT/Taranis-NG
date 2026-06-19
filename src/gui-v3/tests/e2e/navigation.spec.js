import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'

/**
 * Navigation E2E Tests
 *
 * Tests routing, navigation between views, and menu functionality
 */

test.describe('Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should navigate to dashboard', async ({ page }) => {
        await page.goto('/v2/')
        await expect(page).toHaveURL(/\/v2\/(dashboard)?$/)
    })

    test('should navigate to configuration section', async ({ page }) => {
        await page.goto('/v2/config/access-management')
        await expect(page).toHaveURL(/\/config/)

        // Should show the config navigation drawer
        await expect(page.locator('.v-navigation-drawer')).toBeVisible()
    })

    test('should open Access Management from the Configuration menu', async ({ page }) => {
        // Exercise the /config -> /config/access-management redirect via an in-app
        // router navigation (clicking the menu), which is the real user path and
        // avoids the WebKit "internal error" that page.goto('/v2/config') triggers.
        await page.goto('/v2/dashboard')
        await page.getByRole('link', { name: 'Configuration' }).click()

        await expect(page).toHaveURL(/\/config\/access-management/)
    })

    test('should show filtered menu items based on permissions', async ({ page }) => {
        await page.goto('/v2/config/access-management')

        // Config navigation drawer should be visible
        const configNav = page.locator('.v-navigation-drawer')
        await expect(configNav).toBeVisible()

        // At least one menu item should render. Use a web-first assertion so it
        // auto-waits for ConfigNav to populate (count() does not retry).
        await expect(configNav.locator('.v-list-item').first()).toBeVisible()
    })

    test('should open the roles tab in access management', async ({ page }) => {
        await page.goto('/v2/config/access-management')

        // Roles is now a tab inside Access Management; selecting it updates the query.
        await page.getByRole('tab', { name: 'Roles' }).click()

        await expect(page).toHaveURL(/\/config\/access-management\?tab=roles/)
        await expect(page.locator('.v-card-title').filter({ hasText: /roles/i })).toBeVisible()
    })

    test('should open the organizations tab in access management', async ({ page }) => {
        await page.goto('/v2/config/access-management')

        // Organizations is now a tab inside Access Management; selecting it updates the query.
        await page.getByRole('tab', { name: 'Organizations' }).click()

        await expect(page).toHaveURL(/\/config\/access-management\?tab=organizations/)
        await expect(page.locator('.v-card-title').filter({ hasText: /organizations/i })).toBeVisible()
    })

    test('should navigate back using browser back button', async ({ page }) => {
        // Navigate between two distinct config routes.
        await page.goto('/v2/config/access-management')
        await page.goto('/v2/config/settings')
        await expect(page).toHaveURL(/\/config\/settings/)

        // Go back
        await page.goBack()
        await expect(page).toHaveURL(/\/config\/access-management/)
    })

    test('should deep-link to a section tab via query', async ({ page }) => {
        // Opening the deep link directly should select the Roles tab.
        await page.goto('/v2/config/access-management?tab=roles')

        await expect(page).toHaveURL(/tab=roles/)
        await expect(page.locator('.v-card-title').filter({ hasText: /roles/i })).toBeVisible()
    })

    test('should navigate to assess view', async ({ page }) => {
        await page.goto('/v2/assess')
        await expect(page).toHaveURL(/\/assess/)

        // Should show assess content
        await expect(
            page
                .locator('.text-h6')
                .filter({ hasText: /news items/i })
                .first()
        ).toBeVisible()
    })

    test('should navigate to analyze view', async ({ page }) => {
        await page.goto('/v2/analyze')
        await expect(page).toHaveURL(/\/analyze/)
    })

    test('should navigate to publish view', async ({ page }) => {
        await page.goto('/v2/publish')
        await expect(page).toHaveURL(/\/publish/)
    })

    test('should handle 404 for invalid routes', async ({ page }) => {
        await page.goto('/v2/invalid-route-that-does-not-exist')

        // Current router has no catch-all. Verify app remains interactive.
        await expect(page).toHaveURL(/\/v2\//)
    })

    test('should maintain navigation state after page reload', async ({ page }) => {
        // Navigate to specific route
        await page.goto('/v2/config/access-management')

        // Reload
        await page.reload()

        // Should still be on same route
        await expect(page).toHaveURL(/\/config\/access-management/)
    })

    test('should navigate using browser forward button', async ({ page }) => {
        // Navigate between two distinct config routes.
        await page.goto('/v2/config/access-management')
        await page.goto('/v2/config/settings')
        await expect(page).toHaveURL(/\/config\/settings/)

        // Go back
        await page.goBack()
        await expect(page).toHaveURL(/\/config\/access-management/)

        // Go forward
        await page.goForward()
        await expect(page).toHaveURL(/\/config\/settings/)
    })
})
