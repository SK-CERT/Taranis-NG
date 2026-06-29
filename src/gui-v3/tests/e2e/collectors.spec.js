import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'

/**
 * Collectors E2E Tests
 *
 * Covers the tabbed Collectors view: OSINT Sources, OSINT Source Groups and
 * Collectors Nodes. These tabs use the card-grid layout (ContentData) with a
 * shared ToolbarFilter, so assertions target the tabs, the "Add New" button and
 * the shared blue dialog toolbar rather than a data table.
 */

test.describe('Collectors', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/collectors')
        await page.getByRole('tab', { name: 'OSINT Sources' }).waitFor({ state: 'visible', timeout: 5000 })
    })

    test('should show the three collectors tabs', async ({ page }) => {
        await expect(page).toHaveURL(/\/config\/collectors/)
        await expect(page.getByRole('tab', { name: 'OSINT Sources' })).toBeVisible()
        await expect(page.getByRole('tab', { name: 'OSINT Source Groups' })).toBeVisible()
        await expect(page.getByRole('tab', { name: 'Collectors Nodes' })).toBeVisible()
    })

    test('should switch to the OSINT Source Groups tab', async ({ page }) => {
        await page.getByRole('tab', { name: 'OSINT Source Groups' }).click()
        await expect(page).toHaveURL(/tab=groups/)
        await expect(page.getByRole('button', { name: 'Add New' })).toBeVisible()
    })

    test('should deep-link to the Collectors Nodes tab', async ({ page }) => {
        await page.goto('/v2/config/collectors?tab=nodes')
        await expect(page).toHaveURL(/tab=nodes/)
        await expect(page.getByRole('button', { name: 'Add New' })).toBeVisible()
    })

    test('new OSINT source dialog opens with a header toolbar and cancels', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()
        await expect(dialog.locator('.v-toolbar')).toBeVisible()
        await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeVisible()

        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-dialog:visible')).toHaveCount(0)
    })

    test('should validate required fields when creating a collectors node', async ({ page }) => {
        await page.goto('/v2/config/collectors?tab=nodes')
        await page.getByRole('button', { name: 'Add New' }).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()

        await dialog.getByRole('button', { name: 'Save' }).click()

        // Required name/URL fields keep the dialog open with an inline error.
        await expect(dialog.locator('.v-alert')).toBeVisible()
        await expect(dialog).toBeVisible()
    })
})
