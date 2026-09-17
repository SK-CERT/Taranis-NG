import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'
import { createApiContext } from '../helpers/api-cleanup'

/**
 * Report attribute E2E tests.
 *
 * Covers the two halves of the attribute system that a unit test cannot reach:
 * the admin "Edit attribute" dialog (/config/reports → Attributes) and the
 * attribute widgets in the report editor (/analyze → Add New).
 *
 * Every regression here was a real defect:
 *  - constants loaded only on the dialog's first open, because the fetch rode on
 *    the constants table's mount event;
 *  - constants entered while creating an attribute were orphaned server-side;
 *  - the constants table was offered for types that cannot store constants;
 *  - the ENUM widget read a payload key the backend never sends, so its dropdown
 *    was always empty;
 *  - an attribute's default_value was stored but never applied to a new value.
 */

const REPORTS_URL = '/v2/config/reports'
const ANALYZE_URL = '/v2/analyze/local'
const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

// Throwaway attributes created here. Cleanup is scoped to this prefix so parallel
// spec files cannot purge each other's data.
const PREFIX = 'E2E Attr'

async function purgeProbeAttributes(playwright) {
    let ctx
    try {
        ctx = await createApiContext(playwright)
        const res = await ctx.request.get(`${CORE_API}/config/attributes?search=`, {
            headers: { Authorization: `Bearer ${ctx.token}` }
        })
        if (!res.ok()) return
        const { items = [] } = await res.json()
        for (const attribute of items.filter((a) => a.name.startsWith(PREFIX))) {
            await ctx.request.delete(`${CORE_API}/config/attributes/${attribute.id}`, {
                headers: { Authorization: `Bearer ${ctx.token}` }
            })
        }
    } catch {
        // Best effort: never fail the suite on cleanup.
    } finally {
        await ctx?.request.dispose()
    }
}

/** Open the Attributes tab and narrow the list down to one attribute. */
async function findAttributeRow(page, name) {
    await page.locator('.v-card > .v-card-text input').first().fill(name)
    await expect
        .poll(async () =>
            page
                .locator('.elevation-1 table tbody tr')
                .filter({ has: page.locator('td strong').filter({ hasText: new RegExp(`^${name}$`) }) })
                .count()
        )
        .toBeGreaterThan(0)
    return page
        .locator('.elevation-1 table tbody tr')
        .filter({ has: page.locator('td strong').filter({ hasText: new RegExp(`^${name}$`) }) })
        .first()
}

async function openAttributeDialog(page, name) {
    const row = await findAttributeRow(page, name)
    await row.locator('button').first().click()
    await expect(page.locator('.v-dialog.v-overlay--active')).toBeVisible()
    return page.locator('.v-dialog.v-overlay--active')
}

/** The constants card inside the open dialog, or null when the section is hidden. */
function constantsTable(dialog) {
    return dialog.locator('.editable-entity-table')
}

/** The attribute Type combobox. Vuetify's .v-field__input intercepts clicks on the inner input. */
function typeSelect(dialog) {
    return dialog.locator('form .v-select').first()
}

async function pickType(page, dialog, type) {
    // The menu is virtualised, so an option is simply absent from the DOM until the list is
    // scrolled to it. VSelect's html-select keyboard lookup selects by prefix and needs no
    // scrolling at all; space is a menu shortcut rather than a character, so only the first
    // word is typed. The assertion keeps a prefix that matched the wrong type from passing.
    await typeSelect(dialog).click()
    await page.keyboard.type(type.split(' ')[0], { delay: 40 })
    await page.keyboard.press('Escape')
    await expect(typeSelect(dialog).locator('.v-select__selection-text')).toHaveText(type)
}

async function closeAttributeDialog(page) {
    await page.keyboard.press('Escape')
    const discard = page.getByRole('button', { name: 'Close without saving' })
    if (await discard.count()) await discard.first().click()
    await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
}

test.describe('Config - attribute constants', () => {
    test.beforeAll(async ({ playwright }) => {
        await purgeProbeAttributes(playwright)
    })

    test.afterEach(async ({ playwright }) => {
        await purgeProbeAttributes(playwright)
    })

    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto(REPORTS_URL)
        await page.getByRole('tab', { name: 'Attributes' }).click()
        await page.waitForSelector('.elevation-1 table tbody tr')
    })

    test('lists the constants on every open, not just the first', async ({ page }) => {
        // Regression: the fetch used to ride on the constants table's mount event, so a
        // reopen that reused the still-booted dialog content showed "No data available".
        for (const attempt of [1, 2, 3]) {
            const dialog = await openAttributeDialog(page, 'Impact')
            await expect(constantsTable(dialog), `open #${attempt}`).toBeVisible()
            await expect(constantsTable(dialog).locator('tbody tr'), `open #${attempt}`).toHaveCount(7)
            await expect(constantsTable(dialog)).toContainText('Denial of service')
            await closeAttributeDialog(page)
        }
    })

    test('keeps the constants entered while creating an attribute', async ({ page }) => {
        // Regression: add_attribute() cleared the relationship after inserting the rows,
        // which nulled their attribute_id — the constants vanished on the next open.
        const name = `${PREFIX} Enum`
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await dialog.getByLabel('Name', { exact: true }).fill(name)
        await pickType(page, dialog, 'Enumeration')

        for (const value of ['Alpha', 'Beta']) {
            await constantsTable(dialog).getByRole('button', { name: 'Add New' }).click()
            const constantDialog = page.locator('.v-dialog.v-overlay--active').last()
            await constantDialog.getByLabel('Value').fill(value)
            await constantDialog.getByRole('button', { name: 'Save' }).click()
        }
        await dialog.getByRole('button', { name: 'Save' }).first().click()
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)

        const reopened = await openAttributeDialog(page, name)
        await expect(constantsTable(reopened).locator('tbody tr')).toHaveCount(2)
        await expect(constantsTable(reopened)).toContainText('Alpha')
        await expect(constantsTable(reopened)).toContainText('Beta')
    })

    test('offers constants only for the types that can store them', async ({ page }) => {
        // ENUM / RADIO / MULTI_CHOICE own constants; CPE/CVE/CWE hold imported dictionaries.
        for (const name of ['Impact', 'Confidentiality', 'CWE']) {
            const dialog = await openAttributeDialog(page, name)
            await expect(constantsTable(dialog), name).toBeVisible()
            await closeAttributeDialog(page)
        }
        // Everything else would silently discard whatever was entered.
        for (const name of ['Text', 'Number', 'TLP', 'CVSS', 'Date']) {
            const dialog = await openAttributeDialog(page, name)
            await expect(constantsTable(dialog), name).toHaveCount(0)
            await closeAttributeDialog(page)
        }
    })

    test('shows and hides the constants section as the type changes', async ({ page }) => {
        const dialog = await openAttributeDialog(page, 'Impact')
        await expect(constantsTable(dialog).locator('tbody tr')).toHaveCount(7)

        for (const [type, visible] of [
            ['Boolean', false],
            ['String', false],
            ['Enumeration', true]
        ]) {
            await pickType(page, dialog, type)
            if (visible) {
                await expect(constantsTable(dialog).locator('tbody tr'), type).toHaveCount(7)
            } else {
                await expect(constantsTable(dialog), type).toHaveCount(0)
            }
        }
        await closeAttributeDialog(page)
    })

    test('refuses to delete an attribute a report type still uses', async ({ page }) => {
        // attribute_group_item.attribute_id cascades on delete, so deleting an in-use attribute
        // used to strip fields off report types — or fail with a raw foreign key violation once
        // report items held values, which then crashed the error handler itself.
        const row = await findAttributeRow(page, 'Impact')
        const [response] = await Promise.all([
            page.waitForResponse((res) => res.url().includes('/config/attributes/') && res.request().method() === 'DELETE'),
            row.locator('button').nth(1).click()
        ])

        expect(response.status()).toBe(409)
        expect(await response.json()).toMatchObject({ report_types: ['Vulnerability Report'] })
        await expect(page.locator('.v-snackbar')).toContainText('Vulnerability Report')

        // The attribute is still there, and the refusal left the backend usable.
        await page.reload()
        await page.getByRole('tab', { name: 'Attributes' }).click()
        await expect(await findAttributeRow(page, 'Impact')).toBeVisible()
    })

    test('round-trips the default value', async ({ page }) => {
        const name = `${PREFIX} Default`
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await dialog.getByLabel('Name', { exact: true }).fill(name)
        await dialog.getByLabel('Default Value').fill('seeded-default')
        await dialog.getByRole('button', { name: 'Save' }).first().click()
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)

        const reopened = await openAttributeDialog(page, name)
        await expect(reopened.getByLabel('Default Value')).toHaveValue('seeded-default')
    })
})

test.describe('Config - report type fields in use', () => {
    // A report type field that report items hold values for cannot be removed:
    // attribute_group_item is referenced by report_item_attribute with ON DELETE NO ACTION,
    // so the flush used to fail with a raw foreign key violation and lose the whole edit.
    let api
    let reportItemId

    /** Create a report item of the given type and store one value for one of its fields. */
    async function seedReportItemValue(request, token, typeTitle) {
        const headers = { Authorization: `Bearer ${token}` }
        const types = await (
            await request.get(`${CORE_API}/config/report-item-types?search=${encodeURIComponent(typeTitle)}`, { headers })
        ).json()
        const reportType = types.items.find((t) => t.title === typeTitle)
        const groupItem = reportType.attribute_groups.flatMap((g) => g.attribute_group_items).find((gi) => gi.title === 'Impact')

        const created = await request.post(`${CORE_API}/analyze/report-items`, {
            headers,
            data: {
                // id null lets the backend assign one; it stores a posted id verbatim.
                id: null,
                uuid: `e2e-fields-in-use-${Date.now()}`,
                title: 'E2E fields-in-use probe',
                title_prefix: '',
                report_item_type_id: reportType.id,
                news_item_aggregates: [],
                remote_report_items: [],
                attributes: [],
                state_id: null
            }
        })
        const body = await created.json()
        const id = typeof body === 'object' ? body.id : body
        await request.put(`${CORE_API}/analyze/report-items/${id}`, {
            headers,
            data: { add: true, attribute_id: -1, attribute_group_item_id: groupItem.id }
        })

        // Guard the fixture itself: without a stored value there is nothing for the
        // refusal under test to trigger on, and it would pass for the wrong reason.
        const stored = await (await request.get(`${CORE_API}/analyze/report-items/${id}`, { headers })).json()
        expect(stored.attributes.some((a) => a.attribute_group_item_id === groupItem.id)).toBe(true)

        return { id, reportType, groupItem }
    }

    test.beforeAll(async ({ playwright }) => {
        api = await createApiContext(playwright)
    })

    test.afterAll(async () => {
        if (reportItemId !== undefined) {
            await api.request
                .delete(`${CORE_API}/analyze/report-items/${reportItemId}`, { headers: { Authorization: `Bearer ${api.token}` } })
                .catch(() => {})
        }
        await api.request.dispose()
    })

    test('refuses to remove a field whose values report items still hold', async () => {
        const headers = { Authorization: `Bearer ${api.token}` }
        const seeded = await seedReportItemValue(api.request, api.token, 'Vulnerability Report')
        reportItemId = seeded.id

        // Strip the field the report item has a value for.
        const stripped = JSON.parse(JSON.stringify(seeded.reportType))
        for (const group of stripped.attribute_groups) {
            group.attribute_group_items = group.attribute_group_items
                .filter((gi) => gi.id !== seeded.groupItem.id)
                .map((gi) => ({ ...gi, attribute_id: gi.attribute.id, attribute: undefined }))
        }

        const refused = await api.request.put(`${CORE_API}/config/report-item-types/${stripped.id}`, { headers, data: stripped })
        expect(refused.status()).toBe(409)
        expect(await refused.json()).toMatchObject({ fields_in_use: { Impact: 1 } })

        // The refusal must leave the report type intact and the backend usable.
        const after = await (await api.request.get(`${CORE_API}/config/report-item-types?search=Vulnerability`, { headers })).json()
        const stillThere = after.items[0].attribute_groups.flatMap((g) => g.attribute_group_items).some((gi) => gi.id === seeded.groupItem.id)
        expect(stillThere).toBe(true)
    })

    test('refuses to delete a report type that report items are based on', async () => {
        const headers = { Authorization: `Bearer ${api.token}` }
        const types = await (await api.request.get(`${CORE_API}/config/report-item-types?search=Vulnerability`, { headers })).json()
        const reportType = types.items[0]

        const refused = await api.request.delete(`${CORE_API}/config/report-item-types/${reportType.id}`, { headers })
        expect(refused.status()).toBe(409)
        expect((await refused.json()).report_item_count).toBeGreaterThan(0)
    })
})

test.describe('Report editor - attribute widgets', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto(ANALYZE_URL)
        await page.waitForSelector('.v-container')
    })

    /** The expansion panel wrapping one attribute of the open report form. */
    function attributePanel(dialog, page, title) {
        return dialog
            .locator('.item-panel')
            .filter({ has: page.locator('.v-expansion-panel-title').filter({ hasText: new RegExp(`^\\s*${title}\\s*$`) }) })
            .first()
    }

    async function openNewReport(page, type = 'Vulnerability Report') {
        await page.getByRole('button', { name: 'Add New' }).first().click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        await dialog.getByLabel('Report item type').click()
        await page
            .locator('.v-overlay__content .v-list-item-title')
            .filter({ hasText: new RegExp(`^${type}$`) })
            .click()
        return dialog
    }

    test('an ENUM attribute offers its configured constants', async ({ page }) => {
        // Regression: the widget read `attribute.enum_values`, a key the backend never
        // emits (it sends `attribute_enums`), so the dropdown was always empty.
        const dialog = await openNewReport(page)
        const impact = attributePanel(dialog, page, 'Impact')

        await impact.locator('button[title="Add new value to this attribute"]').first().click()
        await impact.locator('.v-select').first().click()

        const options = page.locator('.v-overlay__content .v-list-item-title')
        await expect(options).toHaveCount(7)
        await options.filter({ hasText: /^Denial of service$/ }).click()
        await expect(impact.locator('.v-select__selection-text')).toHaveText('Denial of service')
    })
})
