import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'
import {
    createApiContext,
    getFirstReportItemTypeId,
    getCompletedStateId,
    getInitialStateId,
    createReportItem,
    updateReportItemState,
    cleanupSeedData,
    findAggregateIdByTitle
} from '../helpers/api-seed'

/**
 * Assess dual-badge E2E Tests
 *
 * Verifies that news items linked to report items show two separate chips:
 *  - orange "Analysis in progress" for non-final reports
 *  - green "Analyzed" for completed (final) reports
 *
 * The news item is created via the GUI "Add News Item" dialog (tests that flow),
 * then report items are linked via the API. Cleanup is via the API afterward.
 */

const ASSESS_URL = '/v2/assess'
const NEWS_ITEM_TITLE = 'E2E Badge Test Item'

test.describe('Assess report badges', () => {
    let apiCtx
    let aggregateId
    let inProgressReportId
    let completedReportId
    let reportItemTypeId
    let completedStateId
    let initialStateId

    test.beforeAll(async ({ playwright }) => {
        apiCtx = await createApiContext(playwright)
        const { request, token } = apiCtx

        reportItemTypeId = await getFirstReportItemTypeId(request, token)
        completedStateId = await getCompletedStateId(request, token)
        initialStateId = await getInitialStateId(request, token)
    })

    test.afterAll(async () => {
        if (apiCtx) {
            await cleanupSeedData(apiCtx.request, apiCtx.token, {
                reportItemIds: [inProgressReportId, completedReportId].filter(Boolean),
                aggregateIds: [aggregateId].filter(Boolean)
            })
            await apiCtx.request.dispose()
        }
    })

    test('create a news item via the GUI Add News Item dialog', async ({ page }) => {
        await login(page)
        await page.goto(ASSESS_URL)

        // Wait for the toolbar to render. Use exact match to avoid matching
        // the empty-state "No news items found" paragraph.
        await expect(page.getByText('News Items', { exact: true })).toBeVisible({ timeout: 10000 })

        // The "Add New" button only appears when manual OSINT sources are configured.
        const addBtn = page.getByRole('button', { name: 'Add New' })
        await expect(addBtn).toBeVisible({ timeout: 5000 })

        // Open the Add News Item dialog.
        await addBtn.click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // Fill in the form. The title field is the first text input in the form.
        await dialog.locator('input[type="text"]').first().fill(NEWS_ITEM_TITLE)
        await dialog.locator('textarea').first().fill('News item for dual-badge testing')
        await dialog.locator('input[type="text"]').nth(1).fill('E2E')

        // Save — the dialog closes after a short success delay.
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        // The news item should appear in the Assess list.
        await expect(page.getByText(NEWS_ITEM_TITLE)).toBeVisible({ timeout: 10000 })

        // Look up the aggregate ID via the API so we can attach report items.
        const { request, token } = apiCtx
        aggregateId = await findAggregateIdByTitle(request, token, NEWS_ITEM_TITLE)

        // Create an in-progress report item linked to the aggregate.
        inProgressReportId = await createReportItem(request, token, {
            aggregateId,
            title: 'E2E Badge In-Progress Report',
            reportItemTypeId,
            stateId: initialStateId
        })

        // Create a completed report item linked to the aggregate.
        completedReportId = await createReportItem(request, token, {
            aggregateId,
            title: 'E2E Badge Completed Report',
            reportItemTypeId,
            stateId: completedStateId
        })
        // If the report was created in a non-final state, force it to completed.
        if (completedReportId && initialStateId === completedStateId) {
            await updateReportItemState(request, token, completedReportId, completedStateId)
        }
    })

    test('should show orange "Analysis in progress" badge for in-progress reports', async ({ page }) => {
        await login(page)
        await page.goto(ASSESS_URL)

        // Find the card containing the seeded news-item title.
        const card = page.locator('.aggregate-card-wrapper').filter({ hasText: NEWS_ITEM_TITLE })
        await expect(card).toBeVisible({ timeout: 10000 })

        // The orange in-progress chip should be present.
        const inProgressChip = card.locator('.v-chip').filter({ hasText: /Analysis in progress/i })
        await expect(inProgressChip.first()).toBeVisible()
    })

    test('should show green "Analyzed" badge for completed reports', async ({ page }) => {
        await login(page)
        await page.goto(ASSESS_URL)

        const card = page.locator('.aggregate-card-wrapper').filter({ hasText: NEWS_ITEM_TITLE })
        await expect(card).toBeVisible({ timeout: 10000 })

        // The green analyzed chip should be present.
        const analyzedChip = card.locator('.v-chip').filter({ hasText: /Analyzed/i })
        await expect(analyzedChip.first()).toBeVisible()
    })

    test('clicking the in-progress badge opens the reports dialog with the in-progress report', async ({ page }) => {
        await login(page)
        await page.goto(ASSESS_URL)

        const card = page.locator('.aggregate-card-wrapper').filter({ hasText: NEWS_ITEM_TITLE })
        await expect(card).toBeVisible({ timeout: 10000 })

        const inProgressChip = card
            .locator('.v-chip')
            .filter({ hasText: /Analysis in progress/i })
            .first()
        await expect(inProgressChip).toBeVisible()
        await inProgressChip.click()

        // Two reports exist total; clicking the in-progress badge filters to 1.
        // With only one in-progress report, it opens directly — check for the dialog.
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })
    })

    test('clicking the analyzed badge opens the reports dialog with the completed report', async ({ page }) => {
        await login(page)
        await page.goto(ASSESS_URL)

        const card = page.locator('.aggregate-card-wrapper').filter({ hasText: NEWS_ITEM_TITLE })
        await expect(card).toBeVisible({ timeout: 10000 })

        const analyzedChip = card
            .locator('.v-chip')
            .filter({ hasText: /Analyzed/i })
            .first()
        await expect(analyzedChip).toBeVisible()
        await analyzedChip.click()

        // With only one completed report, it opens directly.
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })
    })
})
