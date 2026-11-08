import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'

/**
 * Public web: report templates, built-in switches, per-web templates and the node switch.
 *
 * Configuration -> Public Web -> Report templates lists the custom templates (a product preset's
 * page, or a report item type's block) and the built-ins public-web falls back on. A template can
 * be limited to some webs; two templates of one target cannot claim the same web. The template
 * editor checks the Jinja source when saving and offers completions while typing.
 *
 * Everything is created through the API under an "E2E" name and removed again; the node gets no
 * API URL, so nothing tries to reach a running public-web node.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

async function adminHeaders(request) {
    const response = await request.post(`${CORE_API}/auth/login`, { data: { username: 'admin', password: 'admin' } })
    const { access_token: token } = await response.json()
    return { Authorization: `Bearer ${token}` }
}

async function firstProductPresetId(request, headers) {
    const response = await request.get(`${CORE_API}/config/product-presets?search=`, { headers })
    const body = await response.json()
    return body.items?.[0]?.id ?? null
}

async function templatesNamed(request, headers, prefix) {
    const response = await request.get(`${CORE_API}/config/public-web-templates?search=`, { headers })
    const body = await response.json()
    return (body.items || []).filter((template) => String(template.name).startsWith(prefix))
}

async function deleteTemplatesNamed(request, headers, prefix) {
    for (const template of await templatesNamed(request, headers, prefix)) {
        await request.delete(`${CORE_API}/config/public-web-templates/${template.id}`, { headers })
    }
}

/** Both groups below give the same product preset a template for every web: start clean of either. */
async function deleteE2ETemplates(request, headers) {
    await deleteTemplatesNamed(request, headers, 'E2E Template')
    await deleteTemplatesNamed(request, headers, 'E2E PerWeb')
}

async function openTemplatesTab(page) {
    await login(page)
    await page.goto('/config/public-web?tab=templates')
    await expect(page.locator('[data-test="builtin-templates"]')).toBeVisible({ timeout: 10000 })
}

/** The template editor's text area (a textarea under the highlighted code). */
const editorOf = (dialog) => dialog.locator('[data-test="template-source"] textarea')

test.describe('Public web report templates', () => {
    const prefix = 'E2E Template'
    let presetId

    test.beforeAll(async ({ playwright }) => {
        const request = await playwright.request.newContext()
        const headers = await adminHeaders(request)
        presetId = await firstProductPresetId(request, headers)
        await deleteE2ETemplates(request, headers)
        await request.dispose()
    })

    test.afterAll(async ({ playwright }) => {
        const request = await playwright.request.newContext()
        await deleteTemplatesNamed(request, await adminHeaders(request), prefix)
        await request.dispose()
    })

    test('creates a product template in the editor, which offers completions', async ({ page }) => {
        test.skip(!presetId, 'no product preset in this environment')
        const name = generateTestName(prefix)
        await openTemplatesTab(page)

        await page.locator('.v-window-item--active').getByRole('button', { name: 'Add New' }).first().click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()

        await dialog.getByLabel('Name', { exact: true }).fill(name)
        await dialog.locator('[data-test="template-target"]').click()
        await page.locator('.v-overlay__content:visible .v-list-item').first().click()

        // Inside {{ }} the editor offers what a product template can use.
        const editor = editorOf(dialog)
        await editor.click()
        await page.keyboard.press('Control+End')
        await page.keyboard.type('\n<p>{{ product.ma')
        const completions = page.locator('.pce-ac-tooltip')
        await expect(completions).toBeVisible()
        await expect(completions).toContainText('max_cvss')
        await page.keyboard.press('Escape')

        // The editor closes brackets and tags as one types; the template itself is set in one go.
        await editor.fill('{% extends "builtin/product_base.html" %}')

        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        const row = page.locator('[data-test="template-row"]').filter({ hasText: name })
        await expect(row).toBeVisible()
        await expect(row.locator('[data-test="template-webs-cell"]')).toHaveText('Every web')
    })

    test('refuses a template that is not valid Jinja, saying where', async ({ page }) => {
        await openTemplatesTab(page)

        await page.locator('.v-window-item--active').getByRole('button', { name: 'Add New' }).first().click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await dialog.getByLabel('Name', { exact: true }).fill(generateTestName(prefix))
        // An item template: the product preset may already have one for every web (the test above).
        await dialog.locator('[data-test="template-kind"]').click()
        await page.locator('.v-overlay__content:visible .v-list-item').filter({ hasText: 'Report item type' }).click()
        await dialog.locator('[data-test="template-target"]').click()
        await page.locator('.v-overlay__content:visible .v-list-item').first().click()

        await editorOf(dialog).fill('{% if %}')
        await dialog.getByRole('button', { name: 'Save' }).click()

        // The dialog stays open with the reason; nothing is stored.
        await expect(dialog.locator('[data-test="template-error"]')).toContainText('line 1')
        await expect(dialog).toBeVisible()
    })
})

test.describe('Public web: templates per web, and the node switch', () => {
    const prefix = 'E2E PerWeb'
    const nodeName = 'E2E PerWeb Node'
    let headers
    let presetId
    let nodeId
    let webIds = []

    test.beforeAll(async ({ playwright }) => {
        const request = await playwright.request.newContext()
        headers = await adminHeaders(request)
        presetId = await firstProductPresetId(request, headers)
        await deleteE2ETemplates(request, headers)

        // A node without an API URL: stored without contacting it, never notified.
        const nodes = await (await request.get(`${CORE_API}/config/public-web-nodes?search=`, { headers })).json()
        for (const node of nodes.items || []) {
            if (node.name === nodeName) await request.delete(`${CORE_API}/config/public-web-nodes/${node.id}`, { headers })
        }
        await request.post(`${CORE_API}/config/public-web-nodes`, {
            headers,
            data: { name: nodeName, description: '', api_url: '', api_key: '' }
        })
        const created = await (
            await request.get(`${CORE_API}/config/public-web-nodes?search=${encodeURIComponent(nodeName)}`, { headers })
        ).json()
        nodeId = created.items.find((node) => node.name === nodeName)?.id
        webIds = []
        for (const web of ['A', 'B']) {
            const response = await request.post(`${CORE_API}/config/public-web-nodes/${nodeId}/webs`, {
                headers,
                data: { name: `E2E PerWeb ${web}`, hostname: `e2e-perweb-${web.toLowerCase()}.example`, config: {} }
            })
            webIds.push((await response.json()).id)
        }
        await request.dispose()
    })

    test.afterAll(async ({ playwright }) => {
        const request = await playwright.request.newContext()
        const adminH = await adminHeaders(request)
        await deleteTemplatesNamed(request, adminH, prefix)
        if (nodeId) {
            for (const webId of webIds)
                await request.delete(`${CORE_API}/config/public-web-nodes/${nodeId}/webs/${webId}`, { headers: adminH })
            await request.delete(`${CORE_API}/config/public-web-nodes/${nodeId}`, { headers: adminH })
        }
        await request.dispose()
    })

    test('one template per web, another for every other web, and no two for the same web', async ({ page, request }) => {
        test.skip(!presetId || !nodeId, 'no product preset or node in this environment')
        const source = '{% extends "builtin/product_base.html" %}'
        const create = (name, ids) =>
            request.post(`${CORE_API}/config/public-web-templates`, {
                headers,
                data: { name, product_preset_id: presetId, source, require_tlp_clear: true, public_web_ids: ids }
            })

        expect((await create(`${prefix} A`, [webIds[0]])).status()).toBe(200)
        expect((await create(`${prefix} rest`, [])).status()).toBe(200)
        const clash = await create(`${prefix} A again`, [webIds[0], webIds[1]])
        expect(clash.status()).toBe(400)
        expect((await clash.json()).error).toMatch(/E2E PerWeb A/)

        await openTemplatesTab(page)
        const rows = page.locator('[data-test="template-row"]')
        await expect(rows.filter({ hasText: `${prefix} A` }).locator('[data-test="template-webs-cell"]')).toHaveText('E2E PerWeb A')
        await expect(rows.filter({ hasText: `${prefix} rest` }).locator('[data-test="template-webs-cell"]')).toHaveText('Every web')
    })

    test('switching a node off keeps it and its webs, and says what it means', async ({ page, request }) => {
        test.skip(!nodeId, 'no node in this environment')
        await login(page)
        await page.goto('/config/public-web?tab=nodes')

        const panel = page.locator('.v-expansion-panel').filter({ hasText: nodeName })
        const nodeSwitch = panel.locator('[data-test="node-enabled"] input')
        await expect(nodeSwitch).toBeChecked()

        await nodeSwitch.click()
        await expect(nodeSwitch).not.toBeChecked()
        await expect
            .poll(async () => {
                const nodes = await (
                    await request.get(`${CORE_API}/config/public-web-nodes?search=${encodeURIComponent(nodeName)}`, { headers })
                ).json()
                return nodes.items.find((node) => node.id === nodeId)?.enabled
            })
            .toBe(false)

        await panel.locator('.v-expansion-panel-title').first().click()
        await expect(panel.locator('[data-test="node-disabled-notice"]')).toBeVisible()

        await nodeSwitch.click()
        await expect(nodeSwitch).toBeChecked()
        await expect(panel.locator('[data-test="node-disabled-notice"]')).toHaveCount(0)
    })
})

test.describe('Public web built-in templates', () => {
    test('a built-in the webs fall back on can be switched off and on; the base ones cannot', async ({ page, request }) => {
        await openTemplatesTab(page)
        const builtins = page.locator('[data-test="builtin-row"]')

        // Templates that others extend or import are always on.
        await expect(builtins.filter({ hasText: 'builtin/product_base.html' }).locator('[data-test="builtin-always-on"]')).toBeVisible()

        const row = builtins.filter({ hasText: 'builtin/item_generic.html' })
        const toggle = row.locator('[data-test="builtin-switch"] input')
        await expect(toggle).toBeChecked()

        try {
            await toggle.click()
            await expect(toggle).not.toBeChecked()
            await expect(row.locator('[data-test="builtin-off-effect"]')).toBeVisible()

            const headers = await adminHeaders(request)
            const stored = await (await request.get(`${CORE_API}/config/public-web-templates/builtin`, { headers })).json()
            expect(stored.items.find((builtin) => builtin.name === 'builtin/item_generic.html').enabled).toBe(false)
        } finally {
            // Leave it on, whatever happened above.
            const headers = await adminHeaders(request)
            await request.put(`${CORE_API}/config/public-web-templates/builtin`, {
                headers,
                data: { name: 'builtin/item_generic.html', enabled: true }
            })
        }
    })
})
