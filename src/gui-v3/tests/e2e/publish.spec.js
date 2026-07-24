import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'
import {
    createApiContext,
    createNewsItem,
    getFirstReportItemTypeId,
    getInitialStateId,
    getFirstOSINTSourceId,
    createReportItem,
    cleanupSeedData
} from '../helpers/api-seed'

/**
 * Publish view E2E tests.
 *
 * Covers the Publish view's confirmation dialogs:
 *   - the publish-confirmation dialog (ConfirmationDialog) showing the product
 *     title, product type and selected publisher preset names
 *   - the "Add Incomplete Reports" confirmation that fires when an in-progress
 *     (non-final) report item is added to a product (gated on the
 *     CASCADE_STATES_ENABLED app setting, which defaults to on in the E2E env)
 *
 * The two describes were previously separate sibling specs
 * (publish-confirm.spec.js and publish-incomplete-reports.spec.js); they're
 * folded here because they exercise the same Publish view's New Product dialog
 * through the same beforeEach (login → /v2/publish) and share the same
 * "confirmation overlay on top of the New Product dialog" assertion shape.
 */

const PUBLISH_URL = '/v2/publish'

test.describe('Publish confirmation dialog', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto(PUBLISH_URL)
        await expect(page).toHaveURL(/\/publish/)
    })

    test('should show product type and publisher preset in the publish confirmation', async ({ page }) => {
        // Open the New Product dialog.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        const form = dialog.locator('.v-card-text').first()

        // Fill a unique title.
        const productTitle = generateTestName('E2E Publish Confirm')
        await form.locator('input').nth(1).fill(productTitle)

        // Select the first product type from the combobox.
        // Vuetify 3 teleports the dropdown to body; scope to visible list items.
        const typeCombo = form.locator('.v-combobox').first()
        await typeCombo.click()
        const dropdownItems = page.locator('.v-overlay__content:visible .v-list-item')
        await dropdownItems.first().click()

        // Select the first publisher preset checkbox.
        const presetCheckbox = form.locator('.v-checkbox').first()
        await presetCheckbox.locator('input').check()

        // Click Publish — this triggers handlePublishConfirmation. Because the form is dirty
        // (we just typed the title), it first opens the "Publish Unsaved Product" unsaved-changes
        // dialog (`showPublishUnsavedConfirmation`), NOT the ConfirmationDialog. We must click
        // "Save and Publish" to save the product first, which then opens the actual
        // ConfirmationDialog (showPublishConfirmation) showing the product title, type, and
        // publisher-preset names — the content this test asserts.
        await dialog.getByRole('button', { name: 'Publish product' }).click()

        // Unsaved-changes dialog ("Publish Unsaved Product") appears ON TOP OF the New Product
        // dialog. Both are .v-dialog.v-overlay--active — scope to the last (topmost) one.
        const unsavedDialog = page.locator('.v-dialog.v-overlay--active').last()
        await expect(unsavedDialog).toBeVisible({ timeout: 5000 })
        await expect(unsavedDialog).toContainText(/Publish Unsaved Product/i)

        // Click "Save and Publish" → saveAndPublish() saves the product, then opens
        // showPublishConfirmation (the ConfirmationDialog whose content we assert below).
        await unsavedDialog.getByRole('button', { name: /Save and Publish/i }).click()

        // The ConfirmationDialog appears ON TOP OF the now-saved New Product dialog (and the
        // unsaved-changes dialog has just closed). Scope by the unique publish-confirmation
        // marker so the Cancel-step assertion below tracks THIS dialog specifically rather
        // than re-evaluating `.last()` (which would resolve to the New Product dialog after
        // the confirmation closes, false-failing the `toHaveCount(0)` check).
        const confirmDialog = page.locator('.v-dialog.v-overlay--active').filter({
            hasText: /Do you really want to publish this product/i
        })
        await expect(confirmDialog).toBeVisible({ timeout: 5000 })

        // The confirmation should contain the product title.
        await expect(confirmDialog).toContainText(productTitle)

        // It should contain the "Product Type" label and the "Publisher Presets" label.
        await expect(confirmDialog).toContainText(/Product Type/i)
        await expect(confirmDialog).toContainText(/Publisher Presets/i)

        // Cancel — don't actually publish a throwaway product.
        await confirmDialog.getByRole('button', { name: 'Cancel' }).click()
        // After cancel only the New Product dialog remains; the confirmation overlay is gone.
        await expect(confirmDialog).toHaveCount(0)
    })

    test('should not render the Publish button without publisher presets', async ({ page }) => {
        // When no publisher presets are configured, canPublish is false and the
        // "Publish product" button is not rendered at all — so there's nothing
        // to confirm. This test verifies that absence rather than trying to click
        // a button that doesn't exist.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()

        const publishBtn = dialog.getByRole('button', { name: 'Publish product' })
        const publishVisible = await publishBtn.count()

        if (publishVisible === 0) {
            // No publisher presets in the environment → Publish button correctly absent.
            // Close the dialog and pass.
            await dialog.locator('.v-toolbar .v-btn').first().click()
            return
        }

        // If publisher presets DO exist, verify the button doesn't trigger a
        // confirmation without selecting one (the validation toast blocks it).
        await publishBtn.click()
        await page.waitForTimeout(1000)

        // Only the New Product dialog should be visible — no confirmation overlay.
        const overlays = page.locator('.v-dialog.v-overlay--active')
        // The confirmation dialog contains "Do you really want" — it should NOT appear.
        await expect(overlays.filter({ hasText: /Do you really want/i })).toHaveCount(0)

        await dialog.locator('.v-toolbar .v-btn').first().click()
    })
})

test.describe('Add Incomplete Reports confirmation', () => {
    // Verifies that adding an in-progress (non-final) report item to a product
    // triggers the "Add Incomplete Reports" confirmation dialog listing the report
    // titles, but only when the CASCADE_STATES_ENABLED app setting is on.
    //
    // Seeds one news-item aggregate + one in-progress report item via the API,
    // then opens the New Product dialog, adds the report via the ReportItemSelector,
    // and asserts the confirmation dialog content.
    let apiCtx
    let aggregateId
    let inProgressReportId
    let reportItemTypeId
    let initialStateId
    let reportTitle

    test.beforeAll(async ({ playwright }) => {
        apiCtx = await createApiContext(playwright)
        const { request, token } = apiCtx

        reportItemTypeId = await getFirstReportItemTypeId(request, token)
        initialStateId = await getInitialStateId(request, token)
        const osintSourceId = await getFirstOSINTSourceId(request, token)

        // Create a news-item aggregate.
        const result = await createNewsItem(request, token, {
            title: 'E2E Incomplete Reports Item',
            description: 'News item for incomplete-reports-confirm testing',
            osintSourceId
        })
        aggregateId = result.aggregateId

        // Create an in-progress report item linked to the aggregate.
        reportTitle = generateTestName('E2E Incomplete Report')
        inProgressReportId = await createReportItem(request, token, {
            aggregateId,
            title: reportTitle,
            reportItemTypeId,
            stateId: initialStateId
        })
    })

    test.afterAll(async () => {
        if (apiCtx) {
            await cleanupSeedData(apiCtx.request, apiCtx.token, {
                reportItemIds: [inProgressReportId].filter(Boolean),
                aggregateIds: [aggregateId].filter(Boolean)
            })
            await apiCtx.request.dispose()
        }
    })

    test('should show the "Add Incomplete Reports" confirmation with report names when cascade is enabled', async ({ page }) => {
        await login(page)
        await page.goto(PUBLISH_URL)

        // Open the New Product dialog.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()

        // Click the "Add report items" button to open the ReportItemSelector.
        await dialog.getByRole('button', { name: /select/i }).click()

        // Wait for the fullscreen selector to appear. It opens ON TOP OF the New Product
        // dialog (both are .v-dialog.v-overlay--active), so scope to the last (topmost) one
        // to avoid a strict-mode violation resolving 2 dialogs.
        const selector = page.locator('.v-dialog.v-overlay--active').last()
        await expect(selector).toBeVisible({ timeout: 5000 })

        // Find and click the seeded in-progress report item's SELECTION CHECKBOX
        // (NOT the card body — clicking the card opens the report-item detail dialog).
        // CardAnalyze.vue → BaseCard.vue renders the checkbox as a `v-checkbox` in a
        // `.checkbox-column` to the LEFT of the card. The card itself has class `.card-item`.
        // The checkbox is OUTSIDE the card DOM, so we need to grab it via the same parent
        // `.card-container` that wraps both. Click the `.v-selection-control__input` element
        // (the actual clickable area of a Vuetify 3 v-checkbox) — clicking the outer `.v-checkbox`
        // wrapper works, but the input wrapper is the more precise target that Vuetify's
        // click handler binds to, avoiding interference from the card's click-catch-all.
        const reportCard = selector.locator('.card-item').filter({ hasText: reportTitle }).first()
        await expect(reportCard).toBeVisible({ timeout: 10000 })
        const cardContainer = reportCard.locator('xpath=ancestor::div[contains(@class,"card-container")][1]')
        const checkboxInput = cardContainer.locator('.v-selection-control__input').first()
        await checkboxInput.click()

        // Click "Add item(s)" to confirm the selection. The button label is the i18n key
        // `common.add_items` = "Add item(s)" (parenthesised, apostrophe, pluralisation),
        // NOT "Add items" — match loosely with case-insensitive `add item` so both
        // current and historical label variants match.
        // Use `force: true` because the ReportItemSelector's fullscreen toolbar has a
        // `v-field__input` (the SearchField text-input) that Playwright sees as "intercepting
        // pointer events" from the Add Items button on the same toolbar row. The button is
        // visible & enabled — force-click bypasses the strict pointer-events check.
        await selector.getByRole('button', { name: /add item/i }).click({ force: true })

        // The "Add Incomplete Reports" confirmation dialog should appear
        // (CASCADE_STATES_ENABLED defaults to on in the E2E environment).
        const confirmDialog = page.locator('.v-dialog.v-overlay--active').filter({ hasText: 'Add Incomplete Reports' })
        await expect(confirmDialog).toBeVisible({ timeout: 5000 })

        // The confirmation should list the in-progress report's title.
        await expect(confirmDialog).toContainText(reportTitle)

        // Cancel — don't actually add the report.
        await confirmDialog.getByRole('button', { name: 'Cancel' }).click()
    })
})
