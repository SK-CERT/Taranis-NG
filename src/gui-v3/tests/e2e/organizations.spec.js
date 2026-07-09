import { test, expect } from '@playwright/test'
import { login, navigateToConfig, openDialog, saveDialog, generateTestName } from '../helpers/test-helpers'

/**
 * Organization Management CRUD E2E Tests
 *
 * Template for testing CRUD operations on other entities
 * Can be replicated for: ACLs, ProductTypes, Attributes, ReportTypes,
 * OSINTSources, OSINTSourceGroups, Collectors, DataProviders, etc.
 */

test.describe('Organization Management', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await navigateToConfig(page, 'Organizations')
        await page.waitForSelector('.v-data-table', { timeout: 5000 })
    })

    test('should display organizations list', async ({ page }) => {
        // Organizations is now the Organizations tab inside the Access Management view.
        await expect(page).toHaveURL(/\/config\/access-management\?tab=organizations/)
        await expect(page.locator('.v-data-table')).toBeVisible()
    })

    test('should create a new organization', async ({ page }) => {
        const orgName = generateTestName('Test Org')

        await openDialog(page, 'New')
        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()

        await dialog.locator('input').first().fill(orgName)
        await dialog.locator('textarea').first().fill('Automated test organization')

        await saveDialog(page)

        // A successful save closes the dialog; a rejected save keeps it open with an inline alert.
        await expect(dialog).toHaveCount(0)

        // The list is paginated, so the new row may land on a later page. Filter by the
        // (unique) name to surface it regardless of which page it's on.
        //
        // Scope the search field to the *active* Access Management window item. The view
        // (Users/Roles/ACL/Organizations tabs) renders a SearchField per tab; Vuetify's
        // v-window-item transition leaves the previous tab's search input cloned in the
        // DOM (hidden) on tab switch, so a page-wide `getByRole('textbox', { name: 'Search' })`
        // is ambiguous (strict-mode violation: resolved to 2 elements).
        const activePanel = page.locator('.v-window-item--active')
        await activePanel.getByRole('textbox', { name: 'Search' }).fill(orgName)
        await expect(page.locator('tbody tr').filter({ hasText: orgName })).toBeVisible()
    })

    test('should require name field', async ({ page }) => {
        await openDialog(page, 'New')
        await page.locator('.v-dialog:visible textarea').first().fill('Description without name')
        await saveDialog(page)

        await expect(page.locator('.v-dialog:visible .v-alert')).toBeVisible()
        await expect(page.locator('.v-dialog')).toBeVisible()
    })

    test('should edit organization', async ({ page }) => {
        // Edit action should be available on existing rows.
        const row = page.locator('tbody tr').first()
        await row.locator('button[title="Edit"]').click()
        await expect(page.locator('.v-data-table.elevation-1')).toBeVisible()
    })

    test('should delete organization', async ({ page }) => {
        // Delete now opens an in-app confirmation dialog (no browser confirm).
        const row = page.locator('tbody tr').first()
        await row.locator('button[title="Delete"]').click()

        const confirmDialog = page.locator('.v-dialog:visible')
        await expect(confirmDialog).toBeVisible()

        // Cancel to keep test data intact.
        await confirmDialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-data-table.elevation-1')).toBeVisible()
    })

    test('should cancel creation of an untouched form without prompting', async ({ page }) => {
        // Cancelling a pristine form closes straight away (no unsaved-changes prompt).
        await openDialog(page, 'New')

        await page
            .locator('.v-dialog:visible button')
            .filter({ hasText: /^Cancel$/ })
            .click()

        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
    })

    // ── Unsaved-changes guard ─────────────────────
    // Cancelling / Escaping a dialog with edits prompts before discarding.
    test('should prompt and discard unsaved changes on cancel', async ({ page }) => {
        await openDialog(page, 'New')
        await page.locator('.v-dialog:visible input').first().fill('Cancelled Organization')

        await page
            .locator('.v-dialog:visible button')
            .filter({ hasText: /^Cancel$/ })
            .click()

        // The unsaved-changes prompt appears instead of closing immediately.
        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()

        await prompt.getByRole('button', { name: 'Close without saving' }).click()

        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
        await expect(page.locator('tbody tr').filter({ hasText: 'Cancelled Organization' })).toHaveCount(0)
    })

    test('should keep editing when choosing "Continue editing" on the prompt', async ({ page }) => {
        await openDialog(page, 'New')
        await page.locator('.v-dialog:visible input').first().fill('Kept Organization')

        await page
            .locator('.v-dialog:visible button')
            .filter({ hasText: /^Cancel$/ })
            .click()

        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()

        // Continue editing dismisses the prompt and leaves the edit dialog open with data intact.
        await prompt.getByRole('button', { name: 'Continue editing' }).click()
        await expect(prompt).toHaveCount(0)

        const editDialog = page.locator('.v-overlay--active')
        await expect(editDialog).toBeVisible()
        await expect(editDialog.locator('input').first()).toHaveValue('Kept Organization')
    })

    test('should prompt when pressing Escape with unsaved changes', async ({ page }) => {
        await openDialog(page, 'New')
        await page.locator('.v-dialog:visible input').first().fill('Escaped Organization')

        await page.keyboard.press('Escape')

        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()

        await prompt.getByRole('button', { name: 'Close without saving' }).click()
        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
    })
})

/**
 * TEMPLATE: Copy this file to test other CRUD entities
 *
 * 1. Copy this file: cp organizations.spec.js product-types.spec.js
 * 2. Update entity name: Organizations → ProductTypes
 * 3. Update navigation: 'Organizations' → 'Product Types'
 * 4. Update URL pattern: /organizations/ → /product-types/
 * 5. Update field names to match entity schema
 * 6. Add entity-specific validations
 *
 * Entities to test (22 total):
 * - ✅ Roles
 * - ✅ Organizations
 * - ⏳ ACL Entries
 * - ⏳ Product Types
 * - ⏳ Attributes
 * - ⏳ Report Types
 * - ⏳ OSINT Sources
 * - ⏳ OSINT Source Groups
 * - ⏳ Collectors Nodes
 * - ⏳ Data Providers
 * - ⏳ Presenters Nodes
 * - ⏳ Publishers Nodes
 * - ⏳ Remote Accesses
 * - ⏳ Remote Nodes
 * - ⏳ Asset Groups
 * - ⏳ External Users
 * - ⏳ Notification Templates
 * - ⏳ Bots Nodes
 * - ⏳ Bot Presets
 * - ⏳ Publisher Presets
 * - ⏳ Users
 * - ⏳ Word Lists
 */
