import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'
import { purgeStatesBestEffort } from '../helpers/api-cleanup'

/**
 * State Workflow (state-entity associations) E2E Tests
 *
 * Covers the "State Workflow" tab of the Workflow view, which maps states to
 * entity types (product / report_item). It uses a v-data-table with an
 * entity-type filter and the shared "Add New" button; the add/edit dialog uses
 * the blue DialogToolbar with entity-type / state / state-type selects.
 *
 * The seeded associations are read-only "system" rows (lock icon), so the CRUD
 * lifecycle test first creates a throwaway state on the States tab to guarantee a
 * collision-free (entity_type, state) pair, then associates / edits / deletes it.
 */

const STATE_WORKFLOW_URL = '/v2/config/workflow?tab=state-workflow'
const STATES_URL = '/v2/config/workflow'

async function createState(page, name) {
    await page.goto(STATES_URL)
    await page.waitForSelector('.v-data-table', { timeout: 5000 })
    await page.getByRole('button', { name: 'Add New' }).click()
    const dialog = page.locator('.v-dialog.v-overlay--active')
    await dialog.locator('input').first().fill(name)
    await dialog.getByRole('button', { name: 'Save' }).click()
    await expect(page.locator('tbody tr').filter({ hasText: name })).toBeVisible()
}

// This spec's throwaway states/associations are named "E2E Assoc State_*". Cleanup is
// scoped to that prefix so parallel spec files can't purge each other's data.
const isE2EAssociationState = (name) => name.startsWith('E2E Assoc State')

// Pick an option from the nth v-select inside the visible dialog.
async function selectOption(page, dialog, index, optionName) {
    await dialog.locator('.v-select').nth(index).click()
    // Options render in a teleported menu. A previously-opened select's listbox lingers in the
    // DOM (hidden), so `getByRole('listbox')` is ambiguous — scope to the *visible* listbox and
    // pick the option by its unique label.
    await page.locator('[role="listbox"]:visible').getByRole('option', { name: optionName, exact: true }).click()
}

test.describe('Workflow - State Workflow', () => {
    // Sweep leftover E2E data from previously crashed runs before starting.
    test.beforeAll(async ({ playwright }) => {
        await purgeStatesBestEffort(playwright, isE2EAssociationState)
    })

    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto(STATE_WORKFLOW_URL)
        await page.waitForSelector('.v-data-table', { timeout: 5000 })
    })

    // Remove anything this file created via the API — survives page death (unlike UI cleanup).
    test.afterEach(async ({ playwright }) => {
        await purgeStatesBestEffort(playwright, isE2EAssociationState)
    })

    test('should deep-link to the State Workflow tab', async ({ page }) => {
        await expect(page).toHaveURL(/tab=state-workflow/)
        await expect(page.getByRole('tab', { name: 'State Workflow' })).toBeVisible()
        await expect(page.locator('.v-data-table')).toBeVisible()
        // The entity-type filter select is part of this tab's toolbar.
        await expect(page.getByRole('combobox', { name: 'Filter by Entity Type' })).toBeVisible()
    })

    test('add dialog opens with the translated title and cancels', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()

        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        // Regression guard: the title used to render the raw
        // "workflow.state_workflow.add_new"/".edit" keys.
        await expect(dialog.locator('.v-toolbar')).toContainText('Add State Association')
        await expect(dialog.locator('.v-toolbar')).not.toContainText('state_workflow')

        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
    })

    test('should keep the dialog open and flag required selects', async ({ page }) => {
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()

        // Entity type and state are required; saving empty fails validation.
        await dialog.getByRole('button', { name: 'Save' }).click()

        await expect(dialog).toBeVisible()
        await expect(dialog.locator('.v-input--error').first()).toBeVisible()
    })

    test('should create, edit and delete a state association', async ({ page }) => {
        const stateName = generateTestName('E2E Assoc State')

        // A fresh state guarantees a collision-free (Product, state) pair. The state and any
        // leftover association are removed via the API in afterEach, so cleanup works even if
        // the UI flow below fails midway.
        await createState(page, stateName)

        await page.goto(STATE_WORKFLOW_URL)
        await page.waitForSelector('.v-data-table', { timeout: 5000 })

        // Create the association: Product + the new state.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await selectOption(page, dialog, 0, 'Product')
        await selectOption(page, dialog, 1, stateName)
        await dialog.getByRole('button', { name: 'Save' }).click()

        // Successful save closes the dialog and shows the new row.
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
        const row = page.locator('tbody tr').filter({ hasText: stateName })
        await expect(row).toBeVisible()
        await expect(row).toContainText('Product')

        // Edit it: the dialog title must be the translated "Edit State Association".
        await row.locator('button[title="Edit"]').click()
        const editDialog = page.locator('.v-dialog.v-overlay--active')
        await expect(editDialog.locator('.v-toolbar')).toContainText('Edit State Association')
        // Bump the sort order and save.
        await editDialog.locator('input[type="number"]').fill('7')
        await editDialog.getByRole('button', { name: 'Save' }).click()
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)

        // Delete the association (it is user-created, hence editable/deletable).
        // Deleting right after an edit must target the real row, not get clobbered
        // by a deferred reset that would send id=-1.
        const editedRow = page.locator('tbody tr').filter({ hasText: stateName })
        await editedRow.locator('button[title="Delete"]').click()
        const confirm = page.locator('.v-dialog.v-overlay--active')
        await expect(confirm).toBeVisible()
        await expect(confirm).not.toContainText('delete_confirm')
        await confirm.getByRole('button', { name: 'Delete', exact: true }).click()
        // The dialog closes (fast signal) and the row is removed. On a failed delete the app
        // now closes the dialog and notifies rather than leaving it silently stuck open.
        await expect(page.locator('.v-dialog.v-overlay--active')).toHaveCount(0)
        await expect(page.locator('tbody tr').filter({ hasText: stateName })).toHaveCount(0)
    })

    test('system associations are read-only (lock instead of edit/delete)', async ({ page }) => {
        // Seeded rows are system associations; at least one must be locked.
        const lockedRow = page
            .locator('tbody tr')
            .filter({ has: page.locator('.mdi-lock-outline') })
            .first()
        await expect(lockedRow).toBeVisible()
        await expect(lockedRow.locator('button[title="Edit"]')).toHaveCount(0)
        await expect(lockedRow.locator('button[title="Delete"]')).toHaveCount(0)
    })
})
