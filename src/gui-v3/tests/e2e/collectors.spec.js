import { test, expect } from '@playwright/test'
import { login, generateTestName, fillRequiredParameters } from '../helpers/test-helpers'

/**
 * Collectors E2E Tests
 *
 * Covers the tabbed Collectors view: OSINT Sources and OSINT Source Groups.
 *
 * Collectors nodes no longer have a tab of their own. They are managed from the OSINT Sources
 * tab, which lists each node as an expansion panel with its sources in a table inside. That
 * puts two different "Add New" buttons on the page - the toolbar's adds a node, a panel's adds
 * a source to that node - so every one of them here is scoped to the region it belongs to
 * rather than picked by name alone.
 */
// Live RSS feed used to exercise the full RSS collector source-creation flow (collector
// selection → parameter fields → save → source appears). Kept here rather than per-test so
// the URL can be swapped in one place.
const RSS_FEED_URL = 'https://cyberfeed.cesnet.cz/feed'

// Seeded by 00-config-seed; the panel every source in this spec is added to.
const NODE_NAME = 'E2E Collectors Node'

// Two "Add New" buttons share the page. Scope each to its own region: by name alone they
// resolve together and Playwright's strict mode fails, or worse, the wrong one wins.
const toolbarAddNew = (page) => page.locator('.config-list-toolbar').getByRole('button', { name: 'Add New' })

const panelAddSource = (page) =>
    page
        .locator('.v-expansion-panel')
        .filter({ hasText: NODE_NAME })
        .locator('.v-expansion-panel-title')
        .getByRole('button', { name: 'Add New' })

// Sources are table rows now, not cards; each row carries its own collect/edit/delete actions.
const sourceRow = (page, name) => page.locator('tbody tr').filter({ hasText: name })

async function deleteSource(page, name) {
    await sourceRow(page, name).first().locator('button[title="Delete"]').click()
    const confirm = page.locator('.v-dialog.v-overlay--active')
    await expect(confirm).toBeVisible({ timeout: 5000 })
    await confirm.getByRole('button', { name: 'Delete' }).click()
    await expect(sourceRow(page, name)).toHaveCount(0, { timeout: 10000 })
}
test.describe('Collectors', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/collectors')
        await page.getByRole('tab', { name: 'OSINT Sources' }).waitFor({ state: 'visible', timeout: 5000 })
    })

    test('should show the two collectors tabs', async ({ page }) => {
        await expect(page).toHaveURL(/\/config\/collectors/)
        await expect(page.getByRole('tab', { name: 'OSINT Sources' })).toBeVisible()
        await expect(page.getByRole('tab', { name: 'OSINT Source Groups' })).toBeVisible()
        // Nodes moved into the OSINT Sources tab; a tab of their own would mean two places to
        // manage the same thing.
        await expect(page.getByRole('tab', { name: 'Collector Nodes' })).toHaveCount(0)
    })

    test('should switch to the OSINT Source Groups tab', async ({ page }) => {
        await page.getByRole('tab', { name: 'OSINT Source Groups' }).click()
        await expect(page).toHaveURL(/tab=groups/)
        await expect(page.getByRole('button', { name: 'Add New' })).toBeVisible()
    })

    test('should manage nodes from the OSINT Sources tab', async ({ page }) => {
        // The seeded node is listed as a panel, with its own Add New for sources beside the
        // toolbar's Add New for nodes.
        const panel = page.locator('.v-expansion-panel').filter({ hasText: NODE_NAME })
        await expect(panel).toBeVisible()
        await expect(toolbarAddNew(page)).toBeVisible()
        await expect(panel.locator('.v-expansion-panel-title').getByRole('button', { name: 'Add New' })).toBeVisible()
    })

    test('new OSINT source dialog opens with a header toolbar and cancels', async ({ page }) => {
        await panelAddSource(page).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()
        await expect(dialog.locator('.v-toolbar')).toBeVisible()
        await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeVisible()

        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-dialog:visible')).toHaveCount(0)
    })

    test('should validate required fields when creating a collectors node', async ({ page }) => {
        await toolbarAddNew(page).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()

        await dialog.getByRole('button', { name: 'Save' }).click()

        // Required name/URL fields keep the dialog open with an inline error.
        await expect(dialog.locator('.v-alert')).toBeVisible()
        await expect(dialog).toBeVisible()
    })

    // ── Unsaved-changes guard ─────────────────────
    // NodeDialog (the shared node create/edit dialog used by Collectors / Presenters /
    // Publishers / Bots Nodes tabs). Cancel with edits must raise the prompt instead of
    // closing silently. Covers the mode-2 fix (missing `capture()` ⇒ prompt never showed).
    test('should prompt and discard unsaved changes when cancelling a new collectors node', async ({ page }) => {
        await toolbarAddNew(page).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()
        await dialog.locator('input').first().fill('Cancelled Collectors Node')

        await dialog.getByRole('button', { name: 'Cancel' }).click()

        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()
        await prompt.getByRole('button', { name: 'Close without saving' }).click()

        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
    })

    test('cancel without edits closes immediately (no false prompt) for a new collectors node', async ({ page }) => {
        // Regression guard for failure mode 1: opening the create dialog and cancelling
        // with NO edits must close right away, without a spurious prompt.
        await toolbarAddNew(page).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()

        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
    })

    // ── OSINT source edit path ───────────────────
    // Editing an existing source triggers PUT /config/osint-sources/{id}. The dialog opens
    // pre-filled from the API record (which carries runtime fields last_attempted,
    // last_collected, last_error_message, state, modified, nested collector, ...). The
    // component must send only editable fields on save — otherwise the backend's
    // NewOSINTSourceSchema forwards e.g. last_attempted to OSINTSource(**data) and crashes:
    //   TypeError: __init__() got an unexpected keyword argument 'last_attempted'
    // The source list is a table grouped by node; the row's edit action opens its dialog.
    async function createManualSource(page, sourceName) {
        await panelAddSource(page).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // The node is preselected by the panel the dialog was opened from.
        // MANUAL_COLLECTOR.
        await dialog.locator('.v-select').nth(1).click()
        await page
            .locator('.v-overlay__content:visible .v-list-item')
            .filter({ hasText: /manual/i })
            .first()
            .click()

        // Fill by label: input.first() hits the Collectors Node v-select's internal input
        // (rendered before the Name text-field) and the value is dropped → validation blocks save.
        await dialog.getByLabel('Name', { exact: true }).fill(sourceName)
        await dialog.getByLabel('Description', { exact: true }).fill('Throwaway source for the edit regression test')
        // PROXY_SERVER (and any other default-less parameter) is required — see helper.
        await fillRequiredParameters(dialog)
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })
        await expect(page.getByText(sourceName).first()).toBeVisible({ timeout: 5000 })
    }

    test('should edit an existing OSINT source and save without crashing (last_attempted payload regression)', async ({ page }) => {
        const sourceName = generateTestName('E2E Edit Source')
        const renamed = `${sourceName} Renamed`

        await createManualSource(page, sourceName)

        // The row's edit action opens the dialog. Unlike the old card, the row itself is not a
        // click target: it carries a switch and a collect button that must not open an editor.
        await sourceRow(page, sourceName).first().locator('button[title="Edit"]').click()

        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })
        // Edit-mode title — confirms the editItem path ran (not the create form).
        await expect(dialog.locator('.v-toolbar')).toContainText('Edit OSINT source')

        // Rename and save by the Name field's label. input.first() resolves to a v-select
        // internal input; the rename would land there instead of the Name field.
        const nameInput = dialog.getByLabel('Name', { exact: true })
        await nameInput.fill('')
        await nameInput.fill(renamed)
        await dialog.getByRole('button', { name: 'Save' }).click()

        // Success: dialog closes (no backend 500 / error alert), and the rename persists.
        await expect(dialog).toHaveCount(0, { timeout: 10000 })
        await expect(page.getByText(renamed).first()).toBeVisible({ timeout: 5000 })
        // No error notification should surface from the failed update path.
        await expect(page.locator('.v-snackbar').filter({ hasText: /error/i })).toHaveCount(0)

        await deleteSource(page, renamed)
    })

    test('should prompt on unsaved changes when cancelling an OSINT source edit', async ({ page }) => {
        const sourceName = generateTestName('E2E Cancel Source')
        await createManualSource(page, sourceName)

        await sourceRow(page, sourceName).first().locator('button[title="Edit"]').click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // Any edit flips the form off its captured baseline → dirty. Target the Name field
        // by label; input.first() would touch a v-select internal input instead.
        const nameInput = dialog.getByLabel('Name', { exact: true })
        await nameInput.fill('')
        await nameInput.fill(`${sourceName} dirty`)
        await dialog.getByRole('button', { name: 'Cancel' }).click()

        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible({ timeout: 5000 })
        await prompt.getByRole('button', { name: 'Close without saving' }).click()
        await expect(page.locator('.v-overlay--active')).toHaveCount(0, { timeout: 5000 })
        // Original name is unchanged.
        await expect(page.getByText(sourceName).first()).toBeVisible({ timeout: 5000 })

        await deleteSource(page, sourceName)
    })

    // ── RSS collector source creation ────────────
    // Selecting the RSS collector exposes its real parameter fields (Proxy server,
    // Refresh interval, Warning interval, Feed URL, User agent, ...). This exercises the
    // parameter-value rendering + payload assembly for a parameter-heavy collector, unlike
    // the Manual collector (no parameters). The Feed URL field is targeted by its label
    // text rather than by DOM order, since the parameter list is long and the position of
    // Feed URL (4th parameter, behind the defaults) is brittle if the collector config adds
    // a default param.
    test('should create an RSS OSINT source pointing at the CESNET cyberfeed', async ({ page }) => {
        const sourceName = generateTestName('E2E RSS Source')

        await panelAddSource(page).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // The node is preselected by the panel the dialog was opened from.
        // RSS_COLLECTOR (listed as "RSS Collector").
        await dialog.locator('.v-select').nth(1).click()
        await page.locator('.v-overlay__content:visible .v-list-item').filter({ hasText: /rss/i }).first().click()
        await expect(dialog.getByLabel('Name', { exact: true })).toBeVisible({ timeout: 5000 })

        // Name + description by label — input.first() resolves to a v-select internal input.
        await dialog.getByLabel('Name', { exact: true }).fill(sourceName)
        await dialog.getByLabel('Description', { exact: true }).fill('CESNET cyberfeed RSS source created via E2E')

        // Fill the Feed URL parameter by its label. Vuetify associates the <label> with the
        // <input>, so the input is reachable via the label text regardless of field order.
        // Use a substring match — the full label is exactly "Feed URL".
        const feedUrlInput = dialog.getByLabel(/Feed URL/i).first()
        await feedUrlInput.fill(RSS_FEED_URL)

        // The RSS collector's remaining default-less parameters (Proxy server, User agent,
        // Limit for article links) are required too; fill them after the Feed URL so the
        // assertion above still targets the real value.
        await fillRequiredParameters(dialog)

        // Save — the core stores the source; no collection runs synchronously here.
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        // The new source appears in its node's table. The row shows the name but not the feed
        // URL (there is no URL column), so only assert the name — asserting the URL would never
        // match and would time out.
        await expect(page.getByText(sourceName).first()).toBeVisible({ timeout: 5000 })

        await deleteSource(page, sourceName)
    })
})
