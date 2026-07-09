import { test, expect } from '@playwright/test'
import { login, navigateToConfig, openDialog, saveDialog, generateTestName } from '../helpers/test-helpers'

/**
 * Role Management CRUD E2E Tests
 *
 * Tests create, read, update, delete operations for roles
 */

test.describe('Role Management', () => {
    test.beforeEach(async ({ page }) => {
        // Login before each test
        await login(page)

        // Navigate to roles section
        await navigateToConfig(page, 'Roles')

        // Wait for roles to load
        await page.waitForSelector('.v-data-table', { timeout: 5000 })
    })

    test('should display roles list', async ({ page }) => {
        // Roles is now the Roles tab inside the Access Management view.
        await expect(page).toHaveURL(/\/config\/access-management\?tab=roles/)

        // Tab content (data table) should be visible
        await expect(page.locator('.v-data-table')).toBeVisible()

        // Should show New button if user has permissions
        const newButton = page.getByRole('button', { name: 'New' })
        const isVisible = await newButton.isVisible().catch(() => false)

        if (isVisible) {
            await expect(newButton).toBeVisible()
        }
    })

    test('should create a new role', async ({ page }) => {
        const roleName = generateTestName('Test Role')

        // Click New button
        await openDialog(page, 'New')

        // Verify dialog is open
        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()

        // Fill form
        await dialog.locator('input').first().fill(roleName)
        await dialog.locator('textarea').first().fill('Automated test role')

        // Save
        await saveDialog(page)

        // A successful save closes the dialog; a rejected save keeps it open with an inline alert.
        // Vuetify keeps a booted dialog's root mounted, so assert on the active-overlay class
        // (toggled with open state) rather than :visible, which still matches a closed dialog.
        await expect(page.locator('.v-overlay--active')).toHaveCount(0)

        // The list is paginated, so the new row may land on a later page. Filter by the
        // (unique) name to surface it regardless of which page it's on.
        //
        // Scope the search field to the *active* Access Management window item. The view
        // (Users/Roles/ACL/Organizations tabs) renders a SearchField per tab; Vuetify's
        // v-window-item transition leaves the previous tab's search input cloned in the
        // DOM (hidden) on tab switch, so a page-wide `getByRole('textbox', { name: 'Search' })`
        // is ambiguous (strict-mode violation: resolved to 2 elements).
        const activePanel = page.locator('.v-window-item--active')
        await activePanel.getByRole('textbox', { name: 'Search' }).fill(roleName)
        await expect(page.locator('tbody tr').filter({ hasText: roleName })).toBeVisible()
    })

    test('should show validation error when creating role without name', async ({ page }) => {
        // Click New button
        await openDialog(page, 'New')

        // Try to save without filling required field
        await saveDialog(page)

        // Should show validation error
        await expect(page.locator('.v-dialog:visible .v-alert.text-error')).toBeVisible()

        // Dialog should remain open
        await expect(page.locator('.v-dialog')).toBeVisible()
    })

    test('should edit an existing role', async ({ page }) => {
        // Edit action should be available on existing rows.
        const row = page.locator('tbody tr').first()
        await row.locator('button[title="Edit"]').click()
        await expect(page.locator('.v-data-table.elevation-1')).toBeVisible()
    })

    test('should delete a role', async ({ page }) => {
        // Delete now opens an in-app confirmation dialog (no browser confirm).
        const row = page.locator('tbody tr').first()
        await row.locator('button[title="Delete"]').click()

        const confirmDialog = page.locator('.v-dialog:visible')
        await expect(confirmDialog).toBeVisible()

        // Cancel to keep test data intact.
        await confirmDialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-data-table.elevation-1')).toBeVisible()
    })

    test('should cancel role creation', async ({ page }) => {
        // Click New button
        await openDialog(page, 'New')

        // Fill some data
        await page.locator('.v-dialog:visible input').first().fill('Cancelled Role')

        // Cancel — with unsaved edits this raises the unsaved-changes prompt.
        await page
            .locator('.v-dialog:visible button')
            .filter({ hasText: /^Cancel$/ })
            .click()

        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()
        await prompt.getByRole('button', { name: 'Close without saving' }).click()

        // Both the prompt and the edit dialog close. Vuetify keeps a booted dialog's root
        // mounted, so assert on the active-overlay class rather than :visible.
        await expect(page.locator('.v-overlay--active')).toHaveCount(0)

        // Role should not be created
        await expect(page.locator('tbody tr').filter({ hasText: 'Cancelled Role' })).toHaveCount(0)
    })

    test('should filter/search roles', async ({ page }) => {
        // Scope to the active Access Management window item — see the create test for why a
        // page-wide search locator is ambiguous (Vuetify leaves a cloned input from the
        // previous tab in the DOM).
        const searchInput = page.locator('.v-window-item--active').getByRole('textbox', { name: 'Search' })
        await expect(searchInput).toBeVisible()

        await searchInput.fill('Admin')

        // Should show only matching role
        await expect(page.locator('tbody tr').filter({ hasText: 'Admin' })).toBeVisible()
    })

    test('should handle duplicate role names', async ({ page }) => {
        // Open dialog and verify save without required data keeps validation visible.
        await openDialog(page, 'New')
        await saveDialog(page)

        // Should keep dialog open and show inline validation state.
        await expect(page.locator('.v-dialog')).toBeVisible()
        await expect(page.locator('.v-dialog:visible .v-alert.text-error')).toBeVisible()
    })
})
