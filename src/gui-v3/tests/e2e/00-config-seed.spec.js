import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { login, generateTestName } from '../helpers/test-helpers'
import { createApiContext, purgeSeedEntitiesBestEffort } from '../helpers/api-seed'

/**
 * E2E Environment Setup: Presenters/Publishers Nodes + Product Type + Publisher Preset
 *
 * This spec exercises the GUI to add a presenters node and a publishers node,
 * then creates a product type and publisher preset via the GUI. This both
 * tests the configuration UI and seeds data for the publish-confirm spec.
 *
 * Prerequisites: the presenters and publishers Docker services must be running
 * (started by test-setup.py). The presenters service is reachable at
 * http://presenters:80 (Docker DNS) from the core container; from the host it's
 * at http://127.0.0.1:${E2E_PRESENTERS_PORT} (default 5092, see docker/.env.e2e).
 * The test stack runs as the `taranis-e2e` compose project on distinct host ports
 * so it can coexist with a production `taranis-ng` stack on the same host.
 */

const __dirname = dirname(fileURLToPath(import.meta.url))
const PRESENTERS_URL = 'http://presenters'
const PUBLISHERS_URL = 'http://publishers'
const COLLECTORS_URL = 'http://collectors'
const API_KEY = readFileSync(resolve(__dirname, '../../../../docker/secrets/api_key.txt'), 'utf-8').trim()

test.describe('Configure environment: nodes + product type + publisher preset', () => {
    // Nodes, product types, and publisher presets are created via the GUI and
    // intentionally left in the E2E environment for downstream specs. They are
    // not cleaned up per-run — the environment is ephemeral (rebuilt by test-setup.py).
    //
    // Adding a node makes the core contact the corresponding service (collectors/presenters/
    // publishers) via Docker DNS. test-setup.py probes each service's /api/v1/isalive before
    // the suite starts so the core→service path is ready; the seed tests therefore don't
    // need an in-test retry (which would fight the dialog's own unsaved-changes guard —
    // cancelling a dirty NodeDialog raises the "Unsaved Changes" prompt, layering dialogs).
    //
    // IDEMPOTENCY GUARD: the three node-add tests below use FIXED names ("E2E Presenters
    // Node" etc.) on unique=True columns. If the E2E stack is reused across runs without a
    // `down -v` wipe (e.g. Playwright's reuseExistingServer keeps test-setup.py from re-running
    // when you click "Run Tests" repeatedly in VS Code), a previous run's node lingers and the
    // next add hits a UniqueViolation → HTTP 500 → the misleading "Could not connect to X
    // node." alert. So ONCE before the whole suite, purge any pre-existing fixed-name nodes.
    //
    // IMPORTANT: this must run in beforeAll, NOT beforeEach. The downstream product-type and
    // publisher-preset tests need the presenters/publishers nodes created by tests 1-3 to
    // still exist (NewProductType.vue auto-selects the first presenters node's first presenter,
    // which renders the v-if="selectedPresenter" Name field). A beforeEach purge would delete
    // the very node test 5 needs → the Name field never renders → timeout.
    test.beforeAll(async ({ playwright }) => {
        await purgeSeedEntitiesBestEffort(playwright)
    })

    test('should add a presenters node via the GUI', async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/presenters?tab=nodes')
        await page.getByRole('tab', { name: 'Presenters Nodes' }).waitFor({ state: 'visible', timeout: 10000 })

        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // Fill by label — NodeDialog has Name/Description/API URL/API Key; the v-textarea for
        // Description may render auxiliary <input> elements that throw off nth() indexing,
        // leaving a required field empty → validation fails → no POST → dialog stays open.
        await dialog.getByLabel('Name', { exact: true }).fill('E2E Presenters Node')
        await dialog.getByLabel('API URL', { exact: true }).fill(PRESENTERS_URL)
        await dialog.getByLabel('API Key', { exact: true }).fill(API_KEY)
        await dialog.getByRole('button', { name: 'Save' }).click()

        await expect(dialog).toHaveCount(0, { timeout: 10000 })
        await expect(page.getByText('E2E Presenters Node')).toBeVisible({ timeout: 5000 })
    })

    test('should add a publishers node via the GUI', async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/publishers?tab=nodes')
        await page.getByRole('tab', { name: 'Publishers Nodes' }).waitFor({ state: 'visible', timeout: 10000 })

        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // Fill by label — see presenters-node test for why nth() is unreliable here.
        await dialog.getByLabel('Name', { exact: true }).fill('E2E Publishers Node')
        await dialog.getByLabel('API URL', { exact: true }).fill(PUBLISHERS_URL)
        await dialog.getByLabel('API Key', { exact: true }).fill(API_KEY)
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

        // Fill by label — see presenters-node test for why nth() is unreliable here.
        await dialog.getByLabel('Name', { exact: true }).fill('E2E Collectors Node')
        await dialog.getByLabel('API URL', { exact: true }).fill(COLLECTORS_URL)
        await dialog.getByLabel('API Key', { exact: true }).fill(API_KEY)
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

        // Fill in name and description by label. Positional input.first() resolves to the
        // Collectors Node v-select's internal <input> (rendered before the Name text-field),
        // where the value is dropped — so the Name field stayed empty and client-side
        // validation kept the dialog open (Save never reached the backend).
        await dialog.getByLabel('Name', { exact: true }).fill(sourceName)
        await dialog.getByLabel('Description', { exact: true }).fill('Manual OSINT source for E2E testing')

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

        // NewProductType.vue auto-selects the first Presenters Node AND the first Presenter as
        // soon as loadNodes() completes (onMounted), which renders the v-if="selectedPresenter"
        // Name/Description fields. We do NOT re-click the dropdowns — doing so re-triggers
        // syncPresenterSelection and can momentarily null selectedPresenter, hiding the Name
        // field and timing out getByLabel('Name'). Instead: wait for the Name field to appear
        // (proves auto-selection finished), then fill by label and save.
        const nameField = dialog.getByLabel('Name', { exact: true })
        await expect(nameField).toBeVisible({ timeout: 15000 })
        await nameField.fill(productTypeName)
        await dialog.getByLabel('Description', { exact: true }).fill('Test product type for E2E publish confirmation')

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

        // NewPublisherPreset.vue auto-selects the first Publishers Node AND the first Publisher
        // once loadNodes() completes (which renders the v-if="selectedPublisher" Name field).
        // We do NOT re-click the dropdowns — doing so re-triggers syncPublisherSelection and can
        // momentarily null selectedPublisher, hiding the Name field. Wait for Name to appear
        // (proves auto-selection finished), then fill and save.
        const nameField = dialog.getByLabel('Name', { exact: true })
        await expect(nameField).toBeVisible({ timeout: 15000 })
        await nameField.fill(presetName)

        // Save.
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        // Verify the preset appears in the list.
        await expect(page.getByText(presetName)).toBeVisible({ timeout: 5000 })
    })
})
