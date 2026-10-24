import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'
import { createApiContext } from '../helpers/api-cleanup'

/**
 * Reports and products in several languages, end to end.
 *
 * A report type lists its language variants. Its labels, and the constants of the choice
 * attributes it uses, get language variants in configuration. A report gets a tab per variant
 * language where a person translates it, and a product gets a title per language, says what a
 * language falls back on, and renders the open tab's language.
 *
 * Translating with AI needs a language model, which the E2E stack does not have; core's and the
 * GUI's unit tests cover it.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

// Everything this spec creates carries the prefix, and its cleanup is scoped to it.
const PREFIX = 'E2E Lang'
const TYPE_TITLE = `${PREFIX} Advisory`
const ATTRIBUTE_NAME = `${PREFIX} Severity`

const headersOf = (token) => ({ Authorization: `Bearer ${token}` })

async function list(api, path) {
    const response = await api.request.get(`${CORE_API}${path}`, { headers: headersOf(api.token) })
    return response.ok() ? ((await response.json()).items ?? []) : []
}

/** Delete what an earlier run of this spec left behind, dependants first. */
async function purge(api) {
    const headers = headersOf(api.token)
    const search = encodeURIComponent(PREFIX)
    const mine = (items, field) => items.filter((item) => String(item[field] ?? '').startsWith(PREFIX))
    for (const product of mine(await list(api, `/publish/products?search=${search}`), 'title')) {
        await api.request.delete(`${CORE_API}/publish/products/${product.id}`, { headers })
    }
    for (const report of mine(await list(api, `/analyze/report-items?search=${search}`), 'title')) {
        await api.request.delete(`${CORE_API}/analyze/report-items/${report.id}`, { headers })
    }
    for (const reportType of mine(await list(api, '/config/report-item-types?search='), 'title')) {
        await api.request.delete(`${CORE_API}/config/report-item-types/${reportType.id}`, { headers })
    }
    for (const attribute of mine(await list(api, '/config/attributes?search='), 'name')) {
        await api.request.delete(`${CORE_API}/config/attributes/${attribute.id}`, { headers })
    }
}

async function findReportType(api) {
    return (await list(api, `/config/report-item-types?search=${encodeURIComponent(TYPE_TITLE)}`)).find((type) => type.title === TYPE_TITLE)
}

async function findAttribute(api) {
    return (await list(api, `/config/attributes?search=${encodeURIComponent(ATTRIBUTE_NAME)}`)).find(
        (attribute) => attribute.name === ATTRIBUTE_NAME
    )
}

/**
 * A report type in English with a Slovak variant: a translatable description and a severity whose
 * constants are this spec's own.
 */
async function seedReportType(api) {
    const headers = headersOf(api.token)
    const text = (await list(api, '/config/attributes?search=')).find((attribute) => attribute.type === 'TEXT')
    await api.request.post(`${CORE_API}/config/attributes`, {
        headers,
        data: {
            id: -1,
            name: ATTRIBUTE_NAME,
            description: 'How bad it is',
            type: 'ENUM',
            default_value: '',
            validator: null,
            validator_parameter: '',
            attribute_enums: [
                { id: -1, index: 0, value: 'High', description: '' },
                { id: -1, index: 1, value: 'Low', description: '' }
            ]
        }
    })
    const severity = await findAttribute(api)
    const field = (index, title, attributeId, translate) => ({
        id: -1,
        index,
        title,
        description: '',
        min_occurrence: 0,
        max_occurrence: 1,
        attribute_id: attributeId,
        ai_provider_id: null,
        ai_prompt: null,
        translate,
        translations: {}
    })
    await api.request.post(`${CORE_API}/config/report-item-types`, {
        headers,
        data: {
            id: -1,
            title: TYPE_TITLE,
            description: 'Advisories in English and Slovak',
            languages: ['en', 'sk'],
            translation_ai_provider_id: null,
            label_language: 'en',
            translations: {},
            attribute_groups: [
                {
                    id: -1,
                    index: 0,
                    title: 'Main',
                    description: '',
                    section: null,
                    section_title: null,
                    translations: {},
                    attribute_group_items: [field(0, 'Description', text.id, true), field(1, 'Severity', severity.id, false)]
                }
            ]
        }
    })
    return findReportType(api)
}

/** An English report of the seeded type; returns its id. */
async function createReport(api, reportType, title) {
    const fields = reportType.attribute_groups[0].attribute_group_items
    const fieldId = (title) => fields.find((field) => field.title === title).id
    const response = await api.request.post(`${CORE_API}/analyze/report-items`, {
        headers: headersOf(api.token),
        data: {
            id: null,
            uuid: null,
            state_id: null,
            report_item_type_id: reportType.id,
            title,
            title_prefix: '',
            news_item_aggregates: [],
            remote_report_items: [],
            attributes: [
                { id: -1, value: 'An attacker can run code.', value_description: '', attribute_group_item_id: fieldId('Description') },
                { id: -1, value: 'High', value_description: '', attribute_group_item_id: fieldId('Severity') }
            ],
            language: 'en'
        }
    })
    expect(response.ok(), await response.text()).toBe(true)
    return await response.json()
}

async function updateReport(api, reportId, data) {
    const response = await api.request.put(`${CORE_API}/analyze/report-items/${reportId}`, {
        headers: headersOf(api.token),
        data: { update: true, ...data }
    })
    expect(response.ok(), await response.text()).toBe(true)
}

async function getReport(api, reportId) {
    return (await api.request.get(`${CORE_API}/analyze/report-items/${reportId}`, { headers: headersOf(api.token) })).json()
}

/** The input whose hint shows ``original`` - a label translation field. */
function translationOf(page, scope, original) {
    return scope
        .locator('.v-input')
        .filter({ has: page.locator('.v-messages__message').filter({ hasText: new RegExp(`^${original}$`) }) })
        .locator('input')
        .first()
}

/** Pick an option of a Vuetify select found by its label (matched exactly); the first one without ``option``. */
async function choose(page, scope, label, option) {
    await scope
        .locator('.v-field')
        .filter({ has: page.locator('label').filter({ hasText: new RegExp(`^${label}$`) }) })
        .first()
        .click()
    const options = page.locator('.v-overlay--active .v-list-item')
    await (option ? options.filter({ hasText: option }) : options).first().click()
}

test.describe('Content languages', () => {
    let api
    let reportType

    test.beforeAll(async ({ playwright }) => {
        api = await createApiContext(playwright)
        await purge(api)
        reportType = await seedReportType(api)
    })

    test.afterAll(async () => {
        await purge(api)
        await api.request.dispose()
    })

    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('a report types labels take a translation, and the original can be copied in', async ({ page }) => {
        await page.goto('/config/reports')
        await page.getByText(TYPE_TITLE, { exact: true }).first().click()
        await page
            .locator('[data-test="report-type-label-tabs"]')
            .getByRole('tab', { name: /Slovak/ })
            .click()
        const labels = page.locator('[data-test="label-translations"]')

        // The type's name, the first field, reads the same in Slovak: copied from the original.
        await labels.locator('[data-test="copy-original"]').first().click()
        await expect(translationOf(page, labels, TYPE_TITLE)).toHaveValue(TYPE_TITLE)
        await translationOf(page, labels, 'Description').fill('Popis')
        await page.locator('.v-dialog.v-overlay--active').getByRole('button', { name: 'Save' }).first().click()

        await expect
            .poll(async () => {
                const saved = await findReportType(api)
                const description = saved?.attribute_groups[0].attribute_group_items.find((field) => field.title === 'Description')
                return [saved?.translations?.sk?.title, description?.translations?.sk?.title]
            })
            .toEqual([TYPE_TITLE, 'Popis'])
    })

    test('an attributes constants are translated in the tab of each language that uses them', async ({ page }) => {
        await page.goto('/config/reports')
        await page.getByRole('tab', { name: 'Attributes' }).click()
        await page.locator('.v-card > .v-card-text input').first().fill(ATTRIBUTE_NAME)
        const row = page
            .locator('.elevation-1 table tbody tr')
            .filter({ has: page.locator('td strong').filter({ hasText: new RegExp(`^${ATTRIBUTE_NAME}$`) }) })
            .first()
        await row.locator('button').first().click()
        const constants = page.locator('.v-dialog.v-overlay--active [data-test="constant-translations"]')

        // English is the labels' language, so Slovak is the only one to translate into.
        await expect(constants.locator('[data-test="constant-language-tabs"]').getByRole('tab')).toHaveText(['Slovak'])
        await constants.locator('tbody tr').filter({ hasText: 'High' }).first().getByTitle('Edit').click()
        const edit = page.locator('.v-dialog.v-overlay--active').last()
        await edit.getByLabel('Value').fill('Vysoká')
        await edit.getByRole('button', { name: 'Save' }).click()

        await expect
            .poll(async () => {
                const attribute = await findAttribute(api)
                const enums = await list(api, `/config/attributes/${attribute.id}/enums?search=&offset=0&limit=10`)
                return enums.find((constant) => constant.value === 'High')?.translations?.sk?.value
            })
            .toBe('Vysoká')
    })

    test('a new report starts in the users default language', async ({ page }) => {
        // The user's settings come as a plain list, not as {items}.
        const settings = await (await api.request.get(`${CORE_API}/config/settings?search=`, { headers: headersOf(api.token) })).json()
        const code = settings.find((setting) => setting.key === 'CONTENT_DEFAULT_LANGUAGE')?.value
        test.skip(!code, 'the admin has no default language for reports and products')

        await page.goto('/analyze/local')
        await page.getByRole('button', { name: 'Add New' }).first().click()

        const name = new Intl.DisplayNames(['en'], { type: 'language' }).of(code)
        await expect(page.locator('[data-dialog="report-item"] [data-test="report-source-language"]')).toContainText(name)
    })

    test('a report is translated by hand, and the translation goes stale when the original changes', async ({ page }) => {
        const title = `${PREFIX} kernel flaw`
        const reportId = await createReport(api, reportType, title)

        await page.goto('/analyze/local')
        await page.getByText(title).first().click()
        const tabs = page.locator('[data-test="report-language-tabs"]')
        await expect(tabs.getByRole('tab')).toHaveText(['English (original)', 'Slovak'])
        await tabs.getByRole('tab', { name: 'Slovak' }).click()
        const name = page.locator('[data-test="report-item-translation"] [data-test="translation-title"] input')
        await name.fill('Chyba v jadre')
        await name.blur()
        await expect.poll(async () => (await getReport(api, reportId)).translations?.sk?.title?.value).toBe('Chyba v jadre')

        // Someone renames the original: the Slovak name was made from the old one.
        await updateReport(api, reportId, { title: `${title} (renamed)` })
        await page.goto('/analyze/local')
        await page.getByText(`${title} (renamed)`).first().click()
        await page.locator('[data-test="report-language-tabs"]').getByRole('tab', { name: 'Slovak' }).click()
        await expect(page.locator('[data-test="report-item-translation"] [data-test="translation-outdated"]').first()).toBeVisible()
    })

    test('a product is titled per language, says what the language falls back on, and renders the open tab', async ({ page }) => {
        const reportTitle = `${PREFIX} driver flaw`
        const reportId = await createReport(api, reportType, reportTitle)
        await updateReport(api, reportId, { language: 'sk', title: 'Chyba v ovládači' })
        await updateReport(api, reportId, { title: `${reportTitle} (renamed)` })
        const productType = (await list(api, '/config/product-types?search=')).find(Boolean)
        test.skip(!productType, 'no product type in this environment')
        const productTitle = `${PREFIX} bulletin`
        const created = await api.request.post(`${CORE_API}/publish/products`, {
            headers: headersOf(api.token),
            data: {
                id: -1,
                title: productTitle,
                description: '',
                product_type_id: productType.id,
                state_id: null,
                report_items: [{ id: reportId }],
                links: [],
                language: 'en'
            }
        })
        const productId = await created.json()

        await page.goto('/publish')
        await page.getByText(productTitle).first().click()
        const tabs = page.locator('[data-test="product-language-tabs"]')
        await expect(tabs.getByRole('tab')).toHaveText(['English (original)', 'Slovak'])
        await tabs.getByRole('tab', { name: 'Slovak' }).click()

        const title = page.locator('[data-test="product-title"] input')
        await title.fill('Týždenný bulletin')
        await title.blur()
        await expect
            .poll(async () => {
                const product = await (
                    await api.request.get(`${CORE_API}/publish/products/${productId}`, { headers: headersOf(api.token) })
                ).json()
                return product.translations?.sk?.title?.value
            })
            .toBe('Týždenný bulletin')

        // The report's Slovak name is outdated, and the product type has no Slovak templates.
        await expect(page.locator('[data-test="notice-outdated"]')).toContainText(`${reportTitle} (renamed)`)
        await expect(page.locator('[data-test="notice-templates"]')).toBeVisible()

        // Downloading renders the open tab's language, once the outdated name is accepted.
        const ticket = page.waitForRequest(
            (request) => request.url().includes('/publish/products/preview-ticket') && request.method() === 'POST'
        )
        await page.getByRole('button', { name: 'Download' }).click()
        await page.getByRole('button', { name: 'Continue anyway' }).click()
        expect((await ticket).postDataJSON().language).toBe('sk')
    })

    test('a product type without templates asks nothing about template languages', async ({ page }) => {
        await page.goto('/config/presenters?tab=types')
        await page.getByRole('button', { name: 'Add New' }).first().click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await choose(page, dialog, 'Presenters Node')
        await choose(page, dialog, 'Presenter', 'JSON')

        await expect(dialog.locator('[data-test="product-type-language-tabs"]')).toHaveCount(0)
        await expect(dialog.locator('[data-test="product-type-template-language"]')).toHaveCount(0)

        // A presenter with templates offers them per language again.
        await choose(page, dialog, 'Presenter', 'PDF')
        await expect(dialog.locator('[data-test="product-type-template-language"]')).toBeVisible()
    })
})
