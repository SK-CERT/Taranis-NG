import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'
import { purgeStatesBestEffort } from '../helpers/api-cleanup'

// This spec's throwaway states are named "E2E State_*" / "E2E Edit_*". Cleanup is scoped to
// those prefixes so parallel spec files can't purge each other's data.
const isE2EState = (name) => name.startsWith('E2E State') || name.startsWith('E2E Edit')

/**
 * Workflow States E2E Tests
 *
 * Covers the "States" tab of the Workflow view (/config/workflow). States use a
 * v-data-table with a search field and the shared "Add New" button. The add/edit
 * dialog uses the blue DialogToolbar; deletion goes through an in-app confirm
 * dialog. Seed data ships read-only "system" states (published / work_in_progress
 * / completed) that expose a lock icon instead of edit/delete actions.
 */

const STATES_URL = '/v2/config/workflow'

test.describe('Workflow - States', () => {
    // Sweep leftover E2E states from previously crashed runs before starting.
    test.beforeAll(async ({ playwright }) => {
        await purgeStatesBestEffort(playwright, isE2EState)
    })

    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto(STATES_URL)
        await page.waitForSelector('.v-data-table', { timeout: 5000 })
    })

    // Remove anything this file created via the API — survives page death (unlike UI cleanup).
    test.afterEach(async ({ playwright }) => {
        await purgeStatesBestEffort(playwright, isE2EState)
    })

    test('should default to the States tab and list states', async ({ page }) => {
        await expect(page).toHaveURL(/\/config\/workflow/)
        await expect(page.getByRole('tab', { name: 'States' })).toBeVisible()
        await expect(page.getByRole('tab', { name: 'State Workflow' })).toBeVisible()
        await expect(page.locator('.v-data-table')).toBeVisible()
        // Seeded system states should be present.
        await expect(page.locator('tbody tr').filter({ hasText: 'Work in Progress' })).toBeVisible()
    })

    test('add-new dialog opens with a header toolbar and cancels', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()

        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        await expect(dialog.locator('.v-toolbar')).toContainText('Add new state')

        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
    })

    test('should keep the dialog open and flag the required name field', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()

        // Saving without a display name fails validation: the dialog stays open and
        // the required field is marked with an inline error.
        await dialog.getByRole('button', { name: 'Save' }).click()

        await expect(dialog).toBeVisible()
        await expect(dialog.locator('.v-input--error').first()).toBeVisible()
    })

    // ── Unsaved-changes guard ─────────────────────
    // Cancel with edits raises the prompt rather than closing silently. Covers the
    // mode-2 fix (missing `capture()` ⇒ prompt never showed) for StatesTab.vue.
    test('should prompt and discard unsaved changes on cancel', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        await dialog.locator('input').first().fill('Cancelled State')

        await dialog.getByRole('button', { name: 'Cancel' }).click()

        // The prompt appears instead of closing immediately.
        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()

        await prompt.getByRole('button', { name: 'Close without saving' }).click()

        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
        await expect(page.locator('tbody tr').filter({ hasText: 'Cancelled State' })).toHaveCount(0)
    })

    test('should keep editing when choosing "Continue editing" on the prompt', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await dialog.locator('input').first().fill('Kept State')

        await dialog.getByRole('button', { name: 'Cancel' }).click()

        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()

        // Continue editing dismisses the prompt and leaves the edit dialog open with data intact.
        await prompt.getByRole('button', { name: 'Continue editing' }).click()
        await expect(prompt).toHaveCount(0)

        const editDialog = page.locator('.v-overlay--active')
        await expect(editDialog).toBeVisible()
        await expect(editDialog.locator('input').first()).toHaveValue('Kept State')
    })

    test('should prompt when pressing Escape with unsaved changes', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await dialog.locator('input').first().fill('Escaped State')

        await page.keyboard.press('Escape')

        const prompt = page.locator('.v-overlay--active').filter({ hasText: 'Unsaved Changes' })
        await expect(prompt).toBeVisible()
        // Discard via the prompt.
        await prompt.getByRole('button', { name: 'Close without saving' }).click()
        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
    })

    test('cancel without edits closes immediately (no false prompt)', async ({ page }) => {
        // Regression guard for failure mode 1: opening the create dialog and cancelling
        // with NO edits must close right away, without a spurious prompt.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()

        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-overlay--active')).toHaveCount(0)
    })

    test('should create a new state and remove it again', async ({ page }) => {
        const stateName = generateTestName('E2E State')

        // Create
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        await dialog.locator('input').first().fill(stateName)
        await dialog.getByRole('button', { name: 'Save' }).click()

        // A successful save closes the dialog and surfaces the new row.
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
        const newRow = page.locator('tbody tr').filter({ hasText: stateName })
        await expect(newRow).toBeVisible()

        // Delete it again (a user-created state is editable, so it exposes a delete action).
        await newRow.locator('button[title="Delete"]').click()

        const confirm = page.locator('.v-dialog.v-overlay--active')
        await expect(confirm).toBeVisible()
        // The standardized ConfirmationDialog shows a generic prompt plus the item name
        // (regression guard: it must not leak the raw "delete_confirm" i18n key).
        await expect(confirm).toContainText(stateName)
        await expect(confirm).not.toContainText('delete_confirm')

        await confirm.getByRole('button', { name: 'Delete' }).click()

        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
        await expect(page.locator('tbody tr').filter({ hasText: stateName })).toHaveCount(0)
    })

    test('should edit a created state', async ({ page }) => {
        const stateName = generateTestName('E2E Edit')
        const renamed = `${stateName} Renamed`

        // Seed a state to edit.
        await page.getByRole('button', { name: 'Add New' }).click()
        let dialog = page.locator('.v-dialog.v-overlay--active')
        await dialog.locator('input').first().fill(stateName)
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
        const row = page.locator('tbody tr').filter({ hasText: stateName })
        await expect(row).toBeVisible()

        // Edit -> rename -> save. (Opening edit right after create must show the edit
        // dialog, not get clobbered by a deferred reset.)
        await row.locator('button[title="Edit"]').click()
        dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog.locator('.v-toolbar')).toContainText('Edit state')
        await dialog.locator('input').first().fill(renamed)
        await dialog.getByRole('button', { name: 'Save' }).click()

        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
        await expect(page.locator('tbody tr').filter({ hasText: renamed })).toBeVisible()

        // Clean up.
        await page.locator('tbody tr').filter({ hasText: renamed }).locator('button[title="Delete"]').click()
        await page.locator('.v-dialog.v-overlay--active').getByRole('button', { name: 'Delete' }).click()
        await expect(page.locator('tbody tr').filter({ hasText: renamed })).toHaveCount(0)
    })

    test('system states are read-only (lock instead of edit/delete)', async ({ page }) => {
        const systemRow = page.locator('tbody tr').filter({ hasText: 'Published' }).first()
        await expect(systemRow).toBeVisible()
        await expect(systemRow.locator('button[title="Edit"]')).toHaveCount(0)
        await expect(systemRow.locator('button[title="Delete"]')).toHaveCount(0)
        await expect(systemRow.locator('.mdi-lock-outline')).toBeVisible()
    })
})
