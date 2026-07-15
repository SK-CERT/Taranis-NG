import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'

/**
 * Collectors E2E Tests
 *
 * Covers the tabbed Collectors view: OSINT Sources, OSINT Source Groups and
 * Collectors Nodes. These tabs use the card-grid layout (ContentData) with a
 * shared ToolbarFilter, so assertions target the tabs, the "Add New" button and
 * the shared blue dialog toolbar rather than a data table.
 */
// Live RSS feed used to exercise the full RSS collector source-creation flow (collector
// selection → parameter fields → save → source appears). Kept here rather than per-test so
// the URL can be swapped in one place.
const RSS_FEED_URL = 'https://cyberfeed.cesnet.cz/feed'
test.describe('Collectors', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/collectors')
        await page.getByRole('tab', { name: 'OSINT Sources' }).waitFor({ state: 'visible', timeout: 5000 })
    })

    test('should show the three collectors tabs', async ({ page }) => {
        await expect(page).toHaveURL(/\/config\/collectors/)
        await expect(page.getByRole('tab', { name: 'OSINT Sources' })).toBeVisible()
        await expect(page.getByRole('tab', { name: 'OSINT Source Groups' })).toBeVisible()
        await expect(page.getByRole('tab', { name: 'Collectors Nodes' })).toBeVisible()
    })

    test('should switch to the OSINT Source Groups tab', async ({ page }) => {
        await page.getByRole('tab', { name: 'OSINT Source Groups' }).click()
        await expect(page).toHaveURL(/tab=groups/)
        await expect(page.getByRole('button', { name: 'Add New' })).toBeVisible()
    })

    test('should deep-link to the Collectors Nodes tab', async ({ page }) => {
        await page.goto('/v2/config/collectors?tab=nodes')
        await expect(page).toHaveURL(/tab=nodes/)
        await expect(page.getByRole('button', { name: 'Add New' })).toBeVisible()
    })

    test('new OSINT source dialog opens with a header toolbar and cancels', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()

        const dialog = page.locator('.v-dialog:visible')
        await expect(dialog).toBeVisible()
        await expect(dialog.locator('.v-toolbar')).toBeVisible()
        await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeVisible()

        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-dialog:visible')).toHaveCount(0)
    })

    test('should validate required fields when creating a collectors node', async ({ page }) => {
        await page.goto('/v2/config/collectors?tab=nodes')
        await page.getByRole('button', { name: 'Add New' }).click()

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
        await page.goto('/v2/config/collectors?tab=nodes')
        await page.getByRole('button', { name: 'Add New' }).click()

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
        await page.goto('/v2/config/collectors?tab=nodes')
        await page.getByRole('button', { name: 'Add New' }).click()

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
    // The source list uses cards (CardCompact); clicking a card opens its edit dialog.
    async function createManualSource(page, sourceName) {
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // First collectors node.
        await dialog.locator('.v-select').first().click()
        await page.locator('.v-overlay__content:visible .v-list-item').first().click()
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
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })
        await expect(page.getByText(sourceName).first()).toBeVisible({ timeout: 5000 })
    }

    test('should edit an existing OSINT source and save without crashing (last_attempted payload regression)', async ({ page }) => {
        const sourceName = generateTestName('E2E Edit Source')
        const renamed = `${sourceName} Renamed`

        await createManualSource(page, sourceName)

        // Clicking the source's card opens the edit dialog (CardCompact emits edit on click).
        await page.locator('.card-compact').filter({ hasText: sourceName }).first().click()

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

        // Clean up the throwaway source via the card's delete action.
        const card = page.locator('.card-compact').filter({ hasText: renamed }).first()
        await card.locator('button[title="Delete"]').click()
        const confirm = page.locator('.v-dialog.v-overlay--active')
        await expect(confirm).toBeVisible({ timeout: 5000 })
        await confirm.getByRole('button', { name: 'Delete' }).click()
        await expect(page.locator('.card-compact').filter({ hasText: renamed })).toHaveCount(0, { timeout: 10000 })
    })

    test('should prompt on unsaved changes when cancelling an OSINT source edit', async ({ page }) => {
        const sourceName = generateTestName('E2E Cancel Source')
        await createManualSource(page, sourceName)

        await page.locator('.card-compact').filter({ hasText: sourceName }).first().click()
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

        // Clean up.
        const card = page.locator('.card-compact').filter({ hasText: sourceName }).first()
        await card.locator('button[title="Delete"]').click()
        const confirm = page.locator('.v-dialog.v-overlay--active')
        await expect(confirm).toBeVisible({ timeout: 5000 })
        await confirm.getByRole('button', { name: 'Delete' }).click()
        await expect(page.locator('.card-compact').filter({ hasText: sourceName })).toHaveCount(0, { timeout: 10000 })
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

        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible({ timeout: 5000 })

        // First collectors node.
        await dialog.locator('.v-select').first().click()
        await page.locator('.v-overlay__content:visible .v-list-item').first().click()
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

        // Save — the core stores the source; no collection runs synchronously here.
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })

        // The new source appears in the OSINT Sources card list. The card shows the source
        // name/description but NOT the feed URL (CardCompact has no URL column for sources),
        // so only assert the name — asserting the URL would never match and time out.
        await expect(page.getByText(sourceName).first()).toBeVisible({ timeout: 5000 })

        // Clean up the throwaway source via the card's delete action.
        const card = page.locator('.card-compact').filter({ hasText: sourceName }).first()
        await card.locator('button[title="Delete"]').click()
        const confirm = page.locator('.v-dialog.v-overlay--active')
        await expect(confirm).toBeVisible({ timeout: 5000 })
        await confirm.getByRole('button', { name: 'Delete' }).click()
        await expect(page.locator('.card-compact').filter({ hasText: sourceName })).toHaveCount(0, { timeout: 10000 })
    })
})
