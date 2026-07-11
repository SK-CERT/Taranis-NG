import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { login, generateTestName } from '../helpers/test-helpers'
import { createApiContext } from '../helpers/api-seed'

/**
 * E2E Environment Setup: Presenters/Publishers Nodes + Product Type + Publisher Preset
 *
 * This spec exercises the GUI to add a presenters node and a publishers node,
 * then creates a product type and publisher preset via the GUI. This both
 * tests the configuration UI and seeds data for the publish-confirm spec.
 *
 * Prerequisites: the presenters and publishers Docker services must be running
 * (started by test-setup.sh). The presenters service is reachable at
 * http://presenters:80 (Docker DNS) from the core container, and at
 * http://127.0.0.1:5002 from the host.
 */

const __dirname = dirname(fileURLToPath(import.meta.url))
const PRESENTERS_URL = 'http://presenters'
const PUBLISHERS_URL = 'http://publishers'
const COLLECTORS_URL = 'http://collectors'
const API_KEY = readFileSync(resolve(__dirname, '../../../../docker/secrets/api_key.txt'), 'utf-8').trim()

test.describe('Configure environment: nodes + product type + publisher preset', () => {
    // Nodes, product types, and publisher presets are created via the GUI and
    // intentionally left in the E2E environment for downstream specs. They are
    // not cleaned up per-run — the environment is ephemeral (rebuilt by test-setup.sh).

    test('should add a presenters node via the GUI', async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/presenters?tab=nodes')
        await page.getByRole('tab', { name: 'Presenters Nodes' }).waitFor({ state: 'visible', timeout: 10000 })

        // Click the "Add New" button inside the Presenters Nodes tab.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // Fill in the node form.
        await dialog.locator('input').nth(0).fill('E2E Presenters Node')
        await dialog.locator('input').nth(1).fill(PRESENTERS_URL)
        await dialog.locator('input').nth(2).fill(API_KEY)

        // Save — the core will contact the presenters service to fetch available presenters.
        await dialog.getByRole('button', { name: 'Save' }).click()

        // The dialog should close on success.
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        // The new node should appear in the list.
        await expect(page.getByText('E2E Presenters Node')).toBeVisible({ timeout: 5000 })
    })

    test('should add a publishers node via the GUI', async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/publishers?tab=nodes')
        await page.getByRole('tab', { name: 'Publishers Nodes' }).waitFor({ state: 'visible', timeout: 10000 })

        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        await dialog.locator('input').nth(0).fill('E2E Publishers Node')
        await dialog.locator('input').nth(1).fill(PUBLISHERS_URL)
        await dialog.locator('input').nth(2).fill(API_KEY)

        await dialog.getByRole('button', { name: 'Save' }).click()

        await expect(dialog).toHaveCount(0, { timeout: 10000 })
        await expect(page.getByText('E2E Publishers Node')).toBeVisible({ timeout: 5000 })
    })

    test('should add a collectors node via the GUI', async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/collectors?tab=nodes')
        await page.getByRole('tab', { name: 'Collectors Nodes' }).waitFor({ state: 'visible', timeout: 10000 })

        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        await dialog.locator('input').nth(0).fill('E2E Collectors Node')
        await dialog.locator('input').nth(1).fill(COLLECTORS_URL)
        await dialog.locator('input').nth(2).fill(API_KEY)

        await dialog.getByRole('button', { name: 'Save' }).click()

        await expect(dialog).toHaveCount(0, { timeout: 10000 })
        await expect(page.getByText('E2E Collectors Node')).toBeVisible({ timeout: 5000 })
    })

    test('should add a manual OSINT source via the GUI', async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/collectors?tab=sources')
        await page.getByRole('tab', { name: 'OSINT Sources' }).waitFor({ state: 'visible', timeout: 10000 })

        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        const sourceName = generateTestName('E2E Manual Source')

        // Select the first collectors node from the dropdown.
        const nodeSelect = dialog.locator('.v-select').first()
        await nodeSelect.click()
        const nodeItems = page.locator('.v-overlay__content:visible .v-list-item')
        await nodeItems.first().click()

        // Select the MANUAL_COLLECTOR from the second dropdown.
        const collectorSelect = dialog.locator('.v-select').nth(1)
        await collectorSelect.click()
        const collectorItems = page.locator('.v-overlay__content:visible .v-list-item')
        // Find the "Manual" collector option.
        const manualItem = collectorItems.filter({ hasText: /manual/i }).first()
        await manualItem.click()

        // Fill in name and description.
        await dialog.locator('input').first().fill(sourceName)
        await dialog.locator('textarea').first().fill('Manual OSINT source for E2E testing')

        // Save.
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        // Verify the source appears in the list.
        await expect(page.getByText(sourceName)).toBeVisible({ timeout: 5000 })
    })

    test('should add a product type via the GUI', async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/presenters?tab=types')
        await page.getByRole('tab', { name: 'Product Types' }).waitFor({ state: 'visible', timeout: 10000 })

        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        const productTypeName = generateTestName('E2E Product Type')

        // Fill title and description.
        await dialog.locator('input').first().fill(productTypeName)
        await dialog.locator('textarea').first().fill('Test product type for E2E publish confirmation')

        // Select the first presenters node from the dropdown.
        const nodeSelect = dialog.locator('.v-select').first()
        await nodeSelect.click()
        const nodeItems = page.locator('.v-overlay__content:visible .v-list-item')
        await nodeItems.first().click()

        // Select the first presenter from the second dropdown (if present).
        const presenterSelect = dialog.locator('.v-select').nth(1)
        const presenterVisible = await presenterSelect.count()
        if (presenterVisible > 0) {
            await presenterSelect.click()
            const presenterItems = page.locator('.v-overlay__content:visible .v-list-item')
            const presenterCount = await presenterItems.count()
            if (presenterCount > 0) {
                await presenterItems.first().click()
            }
        }

        // Save.
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        // Verify the product type appears in the list.
        await expect(page.getByText(productTypeName)).toBeVisible({ timeout: 5000 })
    })

    test('should add a publisher preset via the GUI', async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/publishers?tab=presets')
        await page.getByRole('tab', { name: 'Publisher Presets' }).waitFor({ state: 'visible', timeout: 10000 })

        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        const presetName = generateTestName('E2E Publisher Preset')

        // Fill name.
        await dialog.locator('input').first().fill(presetName)

        // Select the first publishers node from the dropdown.
        const nodeSelect = dialog.locator('.v-select').first()
        await nodeSelect.click()
        const nodeItems = page.locator('.v-overlay__content:visible .v-list-item')
        await nodeItems.first().click()

        // Select the first publisher from the second dropdown (if present).
        const publisherSelect = dialog.locator('.v-select').nth(1)
        const publisherVisible = await publisherSelect.count()
        if (publisherVisible > 0) {
            await publisherSelect.click()
            const publisherItems = page.locator('.v-overlay__content:visible .v-list-item')
            const publisherCount = await publisherItems.count()
            if (publisherCount > 0) {
                await publisherItems.first().click()
            }
        }

        // Save.
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        // Verify the preset appears in the list.
        await expect(page.getByText(presetName)).toBeVisible({ timeout: 5000 })
    })
})
