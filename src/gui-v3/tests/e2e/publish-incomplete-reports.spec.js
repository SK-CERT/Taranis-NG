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

        // Wait for the fullscreen selector to appear.
        const selector = page.locator('.v-dialog.v-overlay--active')
        await expect(selector).toBeVisible({ timeout: 5000 })

        // Find and click the seeded in-progress report item card to select it.
        const reportCard = selector.locator('.card-analyze-stub, [class*="card-analyze"]').filter({ hasText: reportTitle })
        // If the card is rendered as a stub (unit), or a full card (e2e), try clicking by title text.
        if ((await reportCard.count()) > 0) {
            await reportCard.first().click()
        } else {
            // Fallback: click anywhere matching the report title in the selector.
            await selector.getByText(reportTitle).first().click()
        }

        // Click "Add Items" to confirm the selection.
        await selector.getByRole('button', { name: /add items/i }).click()

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
