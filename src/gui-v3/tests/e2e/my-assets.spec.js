import { test, expect } from '@playwright/test'
import { Buffer } from 'node:buffer'
import { createApiContext } from '../helpers/api-seed'
import { generateTestName, login } from '../helpers/test-helpers'

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`
const headers = (token) => ({ Authorization: `Bearer ${token}` })

test.describe('My Assets smoke', () => {
    let apiCtx
    let groupId
    let assetId

    const groupName = generateTestName('E2E_Assets_Group')
    const assetName = generateTestName('E2E_Asset')
    const serial = generateTestName('SERIAL')
    const cpe = 'cpe:2.3:a:e2e:smoke:*:*:*:*:*:*:*:*'

    test.beforeAll(async ({ playwright }) => {
        apiCtx = await createApiContext(playwright)
        const response = await apiCtx.request.post(`${CORE_API}/my-assets/asset-groups`, {
            headers: headers(apiCtx.token),
            data: {
                id: '',
                name: groupName,
                description: 'Temporary group for the My Assets E2E smoke test',
                users: [],
                templates: []
            }
        })
        expect(response.ok(), `Could not create My Assets test group: ${await response.text()}`).toBeTruthy()

        const groupsResponse = await apiCtx.request.get(`${CORE_API}/my-assets/asset-groups`, {
            headers: headers(apiCtx.token),
            params: { search: groupName }
        })
        expect(groupsResponse.ok()).toBeTruthy()
        const groups = (await groupsResponse.json()).items || []
        groupId = groups.find((group) => group.name === groupName)?.id
        expect(groupId, `Created asset group ${groupName} was not returned by the API`).toBeTruthy()
    })

    test.afterAll(async () => {
        if (!apiCtx) return

        if (groupId) {
            if (!assetId) {
                const assetsResponse = await apiCtx.request.get(`${CORE_API}/my-assets/asset-groups/${groupId}/assets`, {
                    headers: headers(apiCtx.token),
                    params: { search: assetName, sort: 'ALPHABETICAL' }
                })
                if (assetsResponse.ok()) {
                    const assets = (await assetsResponse.json()).items || []
                    assetId = assets.find((asset) => asset.name === assetName)?.id
                }
            }

            if (assetId) {
                await apiCtx.request.delete(`${CORE_API}/my-assets/asset-groups/${groupId}/assets/${assetId}`, {
                    headers: headers(apiCtx.token)
                })
            }
            await apiCtx.request.delete(`${CORE_API}/my-assets/asset-groups/${groupId}`, { headers: headers(apiCtx.token) })
        }

        await apiCtx.request.dispose()
    })

    test('navigates to My Assets and persists a new asset with a CPE', async ({ page }) => {
        test.setTimeout(60000)
        await login(page)

        await page.getByRole('link', { name: 'My Assets' }).click()
        const groupLink = page.getByText(groupName, { exact: true })
        await expect(groupLink).toBeVisible({ timeout: 10000 })
        await groupLink.click()
        await expect(page).toHaveURL(new RegExp(`/v2/myassets/group/${groupId}$`), { timeout: 10000 })

        await page.getByRole('button', { name: 'Add Asset' }).click()
        const assetDialog = page.locator('.v-dialog.v-overlay--active').first()
        await expect(assetDialog).toBeVisible()
        await assetDialog.getByLabel('Name', { exact: true }).fill(assetName)
        await assetDialog.getByLabel('Serial Number', { exact: true }).fill(serial)
        await assetDialog.getByLabel('Description', { exact: true }).fill('Created by the lean My Assets smoke test')

        await assetDialog.getByRole('button', { name: 'Import CSV' }).click()
        const importDialog = page.locator('.v-dialog.v-overlay--active').last()
        await expect(importDialog).toBeVisible()
        await importDialog.locator('input[type="file"]').setInputFiles({
            name: 'my-assets-cpes.csv',
            mimeType: 'text/csv',
            buffer: Buffer.from(`value,description\n${cpe},Imported by Playwright`)
        })
        await expect(importDialog.getByText(cpe, { exact: true })).toBeVisible()
        await importDialog.getByRole('button', { name: 'Import', exact: true }).click()
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(1)

        await assetDialog.getByRole('button', { name: 'Save' }).click()
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0, { timeout: 10000 })

        const assetsResponse = await apiCtx.request.get(`${CORE_API}/my-assets/asset-groups/${groupId}/assets`, {
            headers: headers(apiCtx.token),
            params: { search: assetName, sort: 'ALPHABETICAL' }
        })
        expect(assetsResponse.ok()).toBeTruthy()
        const createdAsset = ((await assetsResponse.json()).items || []).find((asset) => asset.name === assetName)
        assetId = createdAsset?.id
        expect(assetId, `Created asset ${assetName} was not returned by the API`).toBeTruthy()
        expect(createdAsset.serial).toBe(serial)
        expect(createdAsset.asset_cpes).toContainEqual({ value: cpe.replaceAll('*', '%') })

        await page.reload()
        const search = page.getByLabel('Search', { exact: true })
        await expect(search).toBeVisible({ timeout: 10000 })
        await search.fill(serial)

        const assetCard = page.locator('.asset-card').filter({ hasText: assetName })
        await expect(assetCard).toBeVisible({ timeout: 10000 })
        await assetCard.click()

        const persistedDialog = page.locator('.v-dialog.v-overlay--active').first()
        await expect(persistedDialog).toBeVisible()
        await expect(persistedDialog.getByText(cpe, { exact: true })).toBeVisible()
    })
})
