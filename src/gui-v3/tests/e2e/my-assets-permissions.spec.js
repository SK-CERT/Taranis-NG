import { test, expect } from '@playwright/test'
import { Buffer } from 'node:buffer'

const encodeJwtPart = (value) => Buffer.from(JSON.stringify(value)).toString('base64url')

const tokenWithPermissions = (permissions) => {
    const header = encodeJwtPart({ alg: 'none', typ: 'JWT' })
    const payload = encodeJwtPart({
        exp: Math.floor(Date.now() / 1000) + 3600,
        sub: 'my-assets-permission-test',
        user_claims: {
            id: 'my-assets-permission-test',
            name: 'My Assets permission test',
            organization_name: 'Test organization',
            permissions
        }
    })
    return `${header}.${payload}.test-signature`
}

const authenticateWith = async (page, permissions) => {
    await page.addInitScript((token) => localStorage.setItem('ACCESS_TOKEN', token), tokenWithPermissions(permissions))
}

const mockAuthenticatedApis = async (page) => {
    await page.route('**/sse', (route) => route.abort())
    await page.route('**/api/v1/**', async (route) => {
        const url = new URL(route.request().url())

        if (url.pathname.endsWith('/my-assets/asset-groups')) {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    total_count: 1,
                    items: [{ id: 'group-1', name: 'Permission test group', description: '' }]
                })
            })
            return
        }

        if (url.pathname.endsWith('/my-assets/asset-groups/group-1/assets')) {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    total_count: 1,
                    items: [
                        {
                            id: 1,
                            asset_group_id: 'group-1',
                            name: 'Read-only server',
                            serial: 'READ-ONLY-1',
                            description: 'Permission boundary fixture',
                            cpes: [],
                            vulnerabilities: [],
                            vulnerabilities_count: 0
                        }
                    ]
                })
            })
            return
        }

        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ total_count: 0, items: [] })
        })
    })
}

test.describe('My Assets permission boundaries', () => {
    test('hides My Assets and redirects its route without access permission', async ({ page }) => {
        await authenticateWith(page, ['ASSESS_ACCESS'])
        await mockAuthenticatedApis(page)

        await page.goto('/v2/myassets')

        await expect(page).toHaveURL(/\/v2\/dashboard$/)
        await expect(page.getByRole('link', { name: 'My Assets' })).toHaveCount(0)
    })

    test('allows read-only access while hiding or disabling mutations', async ({ page }) => {
        await authenticateWith(page, ['MY_ASSETS_ACCESS'])
        await mockAuthenticatedApis(page)

        await page.goto('/v2/myassets')

        await expect(page).toHaveURL(/\/v2\/myassets\/group\/group-1$/)
        await expect(page.getByRole('link', { name: 'My Assets' })).toBeVisible()
        await expect(page.getByText('Read-only server')).toBeVisible()
        await expect(page.getByRole('button', { name: 'Add Asset' })).toHaveCount(0)
        await expect(page.getByRole('button', { name: 'Delete' })).toHaveCount(0)

        await page.getByText('Read-only server').click()
        const assetDialog = page.locator('.v-dialog')
        await expect(assetDialog).toBeVisible()
        await expect(assetDialog.getByRole('button', { name: 'Save' })).toBeDisabled()
        await expect(assetDialog.getByLabel('Name')).toBeDisabled()
    })
})
