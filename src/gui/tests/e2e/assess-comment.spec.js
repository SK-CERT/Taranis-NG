import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'
import { createApiContext, getFirstOSINTSourceId, createNewsItem, cleanupSeedData } from '../helpers/api-seed'

/**
 * Assess comment E2E Tests (issue #1753)
 *
 * The comment of a news item saves itself once the user stops typing. That save refreshes
 * the Assess list, and the refresh used to put the keyboard focus back on the selected card
 * behind the dialog, so whatever the user typed next went nowhere. The comment must keep
 * the focus through the save, and leaving the dialog must still save what was typed last.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`
const NEWS_ITEM_TITLE = `E2E Comment Item ${Date.now()}`

test.describe('Assess comment', () => {
    let apiCtx
    let aggregateId

    test.beforeAll(async ({ playwright }) => {
        apiCtx = await createApiContext(playwright)
        const { request, token } = apiCtx
        const osintSourceId = await getFirstOSINTSourceId(request, token)
        ;({ aggregateId } = await createNewsItem(request, token, { title: NEWS_ITEM_TITLE, osintSourceId }))
    })

    test.afterAll(async () => {
        if (apiCtx) {
            await cleanupSeedData(apiCtx.request, apiCtx.token, { aggregateIds: [aggregateId].filter(Boolean) })
            await apiCtx.request.dispose()
        }
    })

    const savedComment = async () => {
        const res = await apiCtx.request.get(`${CORE_API}/assess/news-item-aggregates-by-group/all`, {
            headers: { Authorization: `Bearer ${apiCtx.token}` },
            params: { offset: 0, limit: 5, sort: 'DATE_DESC', search: NEWS_ITEM_TITLE }
        })
        const items = (await res.json())?.items || []
        return items.find((item) => item.id === aggregateId)?.comments || ''
    }

    test('keeps the focus while the comment saves, and saves on close', async ({ page }) => {
        test.skip(!aggregateId, 'Could not seed a news item')

        await login(page)
        await page.goto('/assess')
        await page.locator('.card-list .card-item').filter({ hasText: NEWS_ITEM_TITLE }).first().click()

        const dialog = page.locator('.v-overlay--active .detail-card')
        await expect(dialog).toBeVisible()
        await dialog.getByRole('tab', { name: 'Comments' }).click()

        const editor = dialog.locator('.rich-text-editor .ProseMirror')
        await editor.click()

        // Pause past the auto-save, and wait for the list refresh that follows it.
        const saved = page.waitForResponse(
            (res) => /\/assess\/news-item-aggregates\/\d+$/.test(res.url()) && res.request().method() === 'PUT'
        )
        const refreshed = page.waitForResponse((res) => res.url().includes('/assess/news-item-aggregates-by-group/'))
        await page.keyboard.type('First part')
        await saved
        await refreshed
        await page.waitForTimeout(500)

        // No "item updated" snackbar for an auto-save: it would be the top overlay for a few
        // seconds, and Vuetify hands Escape to that one instead of the dialog. Counted once
        // rather than awaited, as waiting would just outlast the snackbar's timeout.
        expect(await page.locator('.v-snackbar.v-overlay--active').count()).toBe(0)
        await expect(editor).toBeFocused()
        await page.keyboard.type(' second part')
        await expect(editor).toHaveText('First part second part')

        // Closing straight away, before the auto-save delay, still saves the last words.
        await page.keyboard.type(' and more')
        await page.keyboard.press('Escape')
        await expect(dialog).toBeHidden()
        await expect.poll(savedComment).toBe('<p>First part second part and more</p>')
    })
})
