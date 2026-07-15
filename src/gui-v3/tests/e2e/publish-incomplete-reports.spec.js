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
 * "Add Incomplete Reports" confirmation dialog E2E Tests
 *
 * Verifies that adding an in-progress (non-final) report item to a product
 * triggers the "Add Incomplete Reports" confirmation dialog listing the report
 * titles, but only when the CASCADE_STATES_ENABLED app setting is on.
 *
 * Seeds one news-item aggregate + one in-progress report item via the API,
 * then opens the New Product dialog, adds the report via the ReportItemSelector,
 * and asserts the confirmation dialog content.
 */

const PUBLISH_URL = '/v2/publish'

test.describe('Add Incomplete Reports confirmation', () => {
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
