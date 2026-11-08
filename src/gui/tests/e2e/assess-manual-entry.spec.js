import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'
import { createApiContext, findAggregateIdByTitle, cleanupSeedData, getEntryGroupId } from '../helpers/api-seed'

/**
 * News items entered by hand in Assess go into a source group the user picks - there are no
 * manual OSINT sources any more. The item shows who entered it instead of a source.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

test.describe('Assess manual entry', () => {
    let apiCtx
    const aggregateIds = []

    test.beforeAll(async ({ playwright }) => {
        apiCtx = await createApiContext(playwright)
    })

    test.afterAll(async () => {
        if (apiCtx) {
            await cleanupSeedData(apiCtx.request, apiCtx.token, { aggregateIds: aggregateIds.filter(Boolean) })
            await apiCtx.request.dispose()
        }
    })

    test('an item entered by hand lands in the group and says who entered it', async ({ page }) => {
        const title = generateTestName('E2E Manual Entry')
        const groupId = await getEntryGroupId(apiCtx.request, apiCtx.token)
        test.skip(!groupId, 'no group to enter items into')

        await login(page)
        await page.goto(`/assess/group/${groupId}`)
        const addButton = page.locator('.toolbar-filter').getByRole('button', { name: 'Add New' })
        await expect(addButton).toBeVisible({ timeout: 10000 })
        await addButton.click()

        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        await dialog.getByLabel('Title', { exact: true }).fill(title)
        await dialog.getByLabel('Source', { exact: true }).fill('a phone call')
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        const card = page.locator('.assess-list .card-item').filter({ hasText: title })
        await expect(card).toBeVisible({ timeout: 10000 })
        await expect(card).toContainText(/Manual entry by \S/)

        const aggregateId = await findAggregateIdByTitle(apiCtx.request, apiCtx.token, title)
        aggregateIds.push(aggregateId)
        const detail = await apiCtx.request.get(
            `${CORE_API}/assess/news-item-aggregates-by-group/${groupId}?ids=${aggregateId}&sort=DATE_DESC`,
            {
                headers: { Authorization: `Bearer ${apiCtx.token}` }
            }
        )
        const [item] = (await detail.json()).items
        expect(item.news_items[0].news_item_data.osint_source_id ?? null).toBeNull()
        expect(item.news_items[0].news_item_data.entered_by).toBeTruthy()
    })

    test('the API wants an existing group', async () => {
        const headers = { Authorization: `Bearer ${apiCtx.token}` }
        const item = {
            hash: '',
            title: 'E2E Manual Entry refused',
            review: '',
            source: '',
            link: '',
            content: '',
            author: 'E2E',
            published: '08.11.2026 - 10:00',
            collected: '08.11.2026 - 10:00',
            attributes: []
        }

        const withoutGroup = await apiCtx.request.post(`${CORE_API}/assess/news-items`, { headers, data: item })
        expect(withoutGroup.status()).toBe(400)

        const unknownGroup = await apiCtx.request.post(`${CORE_API}/assess/news-items`, {
            headers,
            data: { ...item, osint_source_group_id: 'no-such-group' }
        })
        expect(unknownGroup.status()).toBe(404)
    })
})
