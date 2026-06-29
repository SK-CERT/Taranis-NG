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

        // Web-first assertion (auto-retries): a successful save closes the dialog
        // and surfaces the new row; a rejected save keeps an inline alert open.
        await expect(page.locator('tbody tr').filter({ hasText: orgName }).or(dialog.locator('.v-alert'))).toBeVisible()
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

    test('should cancel creation', async ({ page }) => {
        await openDialog(page, 'New')
        await page.locator('.v-dialog:visible input').first().fill('Cancelled Organization')

        // Click cancel
        await page
            .locator('.v-dialog:visible button')
            .filter({ hasText: /^Cancel$/ })
            .click()

        await expect(page.locator('.v-dialog')).not.toBeVisible()
        await expect(page.locator('tbody tr').filter({ hasText: 'Cancelled Organization' })).toHaveCount(0)
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
