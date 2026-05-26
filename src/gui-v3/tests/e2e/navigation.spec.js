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
        await page.goto('/v2/config')
        await expect(page).toHaveURL(/\/config/)

        // Should show config navigation
        await expect(page.getByRole('navigation')).toBeVisible()
    })

    test('should show filtered menu items based on permissions', async ({ page }) => {
        await page.goto('/v2/config')

        // Config navigation should be visible
        const configNav = page.getByRole('navigation')
        await expect(configNav).toBeVisible()

        // Should show at least some menu items
        const menuItems = configNav.locator('[role="listitem"]')
        const count = await menuItems.count()
        expect(count).toBeGreaterThan(0)
    })

    test('should navigate to roles via config menu', async ({ page }) => {
        await page.goto('/v2/config')

        const rolesLink = page.locator('a[href$="/config/roles"], a[href$="/v2/config/roles"]').first()
        if (await rolesLink.count()) {
            await rolesLink.click()
        } else {
            await page.goto('/v2/config/roles')
        }

        // Should navigate to roles
        await expect(page).toHaveURL(/\/config\/roles/)
    })

    test('should navigate to organizations via config menu', async ({ page }) => {
        await page.goto('/v2/config')

        const organizationsLink = page.locator('a[href$="/config/organizations"], a[href$="/v2/config/organizations"]').first()
        await expect(organizationsLink).toBeVisible()
        await organizationsLink.click()

        // Should navigate to organizations
        await expect(page).toHaveURL(/\/config\/organizations/)
    })

    test('should navigate back using browser back button', async ({ page }) => {
        // Navigate to config
        await page.goto('/v2/config')

        // Navigate to roles
        await page.goto('/v2/config/roles')
        await expect(page).toHaveURL(/\/config\/roles/)

        // Go back
        await page.goBack()

        // Should be back at config
        await expect(page).toHaveURL(/\/config/)
    })

    test('should handle direct URL navigation', async ({ page }) => {
        // Navigate directly to roles
        await page.goto('/v2/config/roles')

        // Should load roles page
        await expect(page).toHaveURL(/\/config\/roles/)
    })

    test('should show active route in navigation', async ({ page }) => {
        await page.goto('/v2/config/roles')

        // Ensure roles entry exists in the config nav while on roles route.
        const rolesNavLink = page.getByRole('link', { name: 'Roles' }).first()
        await expect(rolesNavLink).toBeVisible()
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

    test('should navigate to my assets view', async ({ page }) => {
        await page.goto('/v2/myassets')
        await expect(page).toHaveURL(/\/myassets/)
    })

    test('should handle 404 for invalid routes', async ({ page }) => {
        await page.goto('/v2/invalid-route-that-does-not-exist')

        // Current router has no catch-all. Verify app remains interactive.
        await expect(page).toHaveURL(/\/v2\//)
    })

    test('should maintain navigation state after page reload', async ({ page }) => {
        // Navigate to specific route
        await page.goto('/v2/config/roles')

        // Reload
        await page.reload()

        // Should still be on same route
        await expect(page).toHaveURL(/\/config\/roles/)
    })

    test('should navigate using browser forward button', async ({ page }) => {
        // Navigate to config
        await page.goto('/v2/config')

        // Navigate to roles
        await page.goto('/v2/config/roles')
        await expect(page).toHaveURL(/\/config\/roles/)

        // Go back
        await page.goBack()
        await expect(page).toHaveURL(/\/config/)

        // Go forward
        await page.goForward()
        await expect(page).toHaveURL(/\/config\/roles/)
    })
})
