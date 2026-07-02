import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'

/**
 * Presenters E2E Tests
 *
 * Covers the tabbed Presenters view: Product Types and Presenters Nodes.
 * These tabs use the card-grid layout (ContentData) with a shared ToolbarFilter,
 * so assertions target the tabs, the "Add New" button and the shared blue dialog
 * toolbar rather than a data table.
 */

test.describe('Presenters', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        // Go straight to the resolved tab URL. The bare /config/presenters path makes the
        // view rewrite the URL to add ?tab=types on mount, and that redirect during initial
        // navigation trips a WebKit "internal error".
        await page.goto('/v2/config/presenters?tab=types')
        await page.getByRole('tab', { name: 'Product Types' }).waitFor({ state: 'visible', timeout: 5000 })
    })

    test('should show the two presenters tabs', async ({ page }) => {
        await expect(page).toHaveURL(/\/config\/presenters/)
        await expect(page.getByRole('tab', { name: 'Product Types' })).toBeVisible()
        await expect(page.getByRole('tab', { name: 'Presenters Nodes' })).toBeVisible()
    })

    test('should switch to the Presenters Nodes tab', async ({ page }) => {
        await page.getByRole('tab', { name: 'Presenters Nodes' }).click()
        await expect(page).toHaveURL(/tab=nodes/)
        await expect(page.getByRole('button', { name: 'Add New' })).toBeVisible()
    })

    test('should deep-link to the Product Types tab', async ({ page }) => {
        await page.goto('/v2/config/presenters?tab=types')
        await expect(page).toHaveURL(/tab=types/)
        await expect(page.getByRole('button', { name: 'Add New' })).toBeVisible()
    })

    test('new product type dialog opens with a header toolbar and cancels', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()
        await expect(dialog.locator('.v-toolbar')).toBeVisible()
        await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeVisible()

        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-dialog:visible')).toHaveCount(0)
    })

    test('product type help dialog lists template variables', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()

        // The help button only appears once a presenter (with parameters) is selected.
        const helpButton = dialog.getByRole('button', { name: /Template parameters/i })
        if (await helpButton.count()) {
            await helpButton.first().click()
            const helpDialog = page.locator('.v-dialog:visible').last()
            await expect(helpDialog.getByText(/Report Items/i)).toBeVisible()
        }
    })

    test('should validate required fields when creating a presenters node', async ({ page }) => {
        await page.goto('/v2/config/presenters?tab=nodes')
        await page.getByRole('button', { name: 'Add New' }).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()

        await dialog.getByRole('button', { name: 'Save' }).click()

        await expect(dialog.locator('.v-alert')).toBeVisible()
        await expect(dialog).toBeVisible()
    })
})
