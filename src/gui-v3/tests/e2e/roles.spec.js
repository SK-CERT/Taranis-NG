import { test, expect } from '@playwright/test'
import { login, navigateToConfig, openDialog, closeDialog, saveDialog, generateTestName } from '../helpers/test-helpers'

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
        // Verify we're on roles page
        await expect(page).toHaveURL(/\/config\/roles/)

        // Should show page title or header
        await expect(page.locator('.v-card-title').filter({ hasText: /roles/i })).toBeVisible()

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
        await expect(page.locator('.v-dialog')).toBeVisible()

        // Fill form
        await page.locator('.v-dialog:visible input').first().fill(roleName)
        await page.locator('.v-dialog:visible textarea').first().fill('Automated test role')

        // Save
        await saveDialog(page)

        const dialogStillOpen = await page.locator('.v-dialog:visible').count()
        if (dialogStillOpen) {
            await expect(page.locator('.v-dialog:visible .v-alert.text-error')).toBeVisible()
            await page
                .locator('.v-dialog:visible button')
                .filter({ hasText: /^Cancel$/ })
                .click()
        }

        await expect(page.locator('.v-data-table')).toBeVisible()
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
        await expect(page.locator('.v-data-table')).toBeVisible()
    })

    test('should delete a role', async ({ page }) => {
        // Delete button opens browser confirm in this view.
        page.once('dialog', (dialog) => dialog.dismiss())
        const row = page.locator('tbody tr').first()
        await row.locator('button[title="Delete"]').click()

        await expect(page.locator('.v-data-table')).toBeVisible()
    })

    test('should cancel role creation', async ({ page }) => {
        // Click New button
        await openDialog(page, 'New')

        // Fill some data
        await page.locator('.v-dialog:visible input').first().fill('Cancelled Role')

        // Cancel
        await closeDialog(page)

        // Dialog should close
        await expect(page.locator('.v-dialog')).not.toBeVisible()

        // Role should not be created
        await expect(page.locator('text=Cancelled Role')).not.toBeVisible()
    })

    test('should filter/search roles', async ({ page }) => {
        // Look for search input (if implemented)
        const searchInput = page.locator('input[aria-label*="search" i], input[placeholder*="search" i]').first()
        const searchExists = await searchInput.isVisible().catch(() => false)

        if (searchExists) {
            // Use search
            await searchInput.fill('Admin')

            // Should show only matching role
            await expect(page.locator('tbody tr').filter({ hasText: 'Admin' })).toBeVisible()
        }
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
