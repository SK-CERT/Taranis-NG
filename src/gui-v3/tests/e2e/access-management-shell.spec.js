import { test, expect } from '@playwright/test'
import { login, openDialog, saveDialog } from '../helpers/test-helpers'

/**
 * Access Management E2E Tests
 *
 * Covers the tabbed Access Management view (Users / Roles / ACL / Organizations),
 * tab deep-linking, and the Users dialog (shared blue DialogToolbar with the
 * Cancel/Save actions in the header). Role and Organization CRUD is covered in
 * their own specs; this suite focuses on the tab container and the Users tab.
 */

test.describe('Access Management', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/access-management')
        await page.waitForSelector('.v-data-table', { timeout: 5000 })
    })

    test('should default to the Users tab', async ({ page }) => {
        await expect(page.getByRole('tab', { name: 'Users', exact: true })).toHaveAttribute('aria-selected', 'true')
        await expect(page.locator('.v-data-table')).toBeVisible()
    })

    test('should switch between all access-management tabs', async ({ page }) => {
        const tabs = [
            ['Roles', 'roles'],
            ['ACL', 'acls'],
            ['Organizations', 'organizations'],
            ['Users', 'users']
        ]

        for (const [name, query] of tabs) {
            await page.getByRole('tab', { name, exact: true }).click()
            await expect(page).toHaveURL(new RegExp(`tab=${query}`))
            await expect(page.locator('.v-data-table')).toBeVisible()
        }
    })

    test('should deep-link to the ACL tab', async ({ page }) => {
        await page.goto('/v2/config/access-management?tab=acls')
        await expect(page).toHaveURL(/tab=acls/)
        await expect(page.getByRole('tab', { name: 'ACL', exact: true })).toHaveAttribute('aria-selected', 'true')
        await expect(page.locator('.v-data-table')).toBeVisible()
    })

    test('new-user dialog has a header toolbar with Cancel and Save', async ({ page }) => {
        await openDialog(page, 'New')

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()
        // Actions live in the blue header toolbar (DialogToolbar), not a bottom bar.
        await expect(dialog.locator('.v-toolbar')).toBeVisible()
        await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeVisible()
        await expect(dialog.getByRole('button', { name: 'Save' })).toBeVisible()
    })

    test('should validate required fields when creating a user', async ({ page }) => {
        await openDialog(page, 'New')
        await saveDialog(page)

        // Saving an empty form keeps the dialog open and surfaces an inline error.
        await expect(page.locator('.v-dialog:visible .v-alert')).toBeVisible()
        await expect(page.locator('.v-dialog:visible')).toBeVisible()
    })

    test('should cancel user creation', async ({ page }) => {
        await openDialog(page, 'New')
        await page.locator('.v-dialog:visible input').first().fill('cancelled-user')

        // Cancel with unsaved edits raises the unsaved-changes prompt; discard to close.
        await page
            .locator('.v-dialog:visible button')
            .filter({ hasText: /^Cancel$/ })
            .click()

        // Vuetify keeps a booted dialog's root mounted, so match on the active-overlay class
        // (toggled with open state) rather than :visible, which still matches a closed dialog.
        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()
        await prompt.getByRole('button', { name: 'Close without saving' }).click()

        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
    })
})
