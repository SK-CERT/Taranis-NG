import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'

/**
 * Attribute extraction rules (Collectors → Attribute extraction rules tab).
 *
 * Creating a rule from this tab once failed on every attempt - the backend required an id the
 * GUI never sends - and a rejected save showed its reason on the page behind the modal, where
 * nobody saw it. These pin both: a rule can be created, and a rejection is explained inside
 * the dialog, in the server's words. Deleting asks first: a rule is live configuration that every
 * collector runs, and the table used to drop it on a single click.
 */

const rowFor = (page, name) => page.locator('tbody tr').filter({ hasText: name })

async function fillRule(dialog, { name, key, pattern }) {
    await dialog.getByLabel('Name', { exact: true }).fill(name)
    await dialog.getByLabel('Attribute key', { exact: true }).fill(key)
    await dialog.getByLabel('Regular expression', { exact: true }).fill(pattern)
}

test.describe('Attribute extraction rules', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto('/v2/config/collectors?tab=extraction')
        await expect(page.getByText('Attribute extraction rules').first()).toBeVisible({ timeout: 10000 })
    })

    test('creates a rule, and explains a rejected one inside the dialog', async ({ page }) => {
        const name = generateTestName('E2E Ticket')
        const dialog = page.locator('.v-dialog.v-overlay--active')

        // A Python-only pattern: named group and inline flag, which a browser RegExp rejects.
        await page.getByRole('button', { name: 'Add New' }).click()
        await expect(dialog).toBeVisible({ timeout: 5000 })
        await fillRule(dialog, { name, key: 'TICKET', pattern: '(?i)inc-(?P<number>\\d+)' })
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 10000 })
        await expect(rowFor(page, name)).toBeVisible({ timeout: 10000 })

        // The same name again: the server refuses, and says why where the user is looking.
        await page.getByRole('button', { name: 'Add New' }).click()
        await expect(dialog).toBeVisible({ timeout: 5000 })
        await fillRule(dialog, { name, key: 'TICKET', pattern: 'INC-\\d+' })
        await dialog.getByRole('button', { name: 'Save' }).click()
        await expect(dialog.locator('.v-alert')).toContainText('already exists', { timeout: 10000 })
        await expect(dialog).toBeVisible()
        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await page.getByRole('button', { name: 'Close without saving' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 5000 })

        // Deleting asks first, and cancelling keeps the rule.
        await rowFor(page, name).locator('button[title="Delete"]').click()
        await expect(dialog).toContainText(name, { timeout: 5000 })
        await dialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(dialog).toHaveCount(0, { timeout: 5000 })
        await expect(rowFor(page, name)).toBeVisible()

        // Confirming deletes it.
        await rowFor(page, name).locator('button[title="Delete"]').click()
        await dialog.getByRole('button', { name: 'Delete' }).click()
        await expect(rowFor(page, name)).toHaveCount(0, { timeout: 10000 })
    })
})
