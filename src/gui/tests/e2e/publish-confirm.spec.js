import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'

/**
 * Publish confirmation dialog E2E Tests
 *
 * Verifies that the publish confirmation dialog (ConfirmationDialog) shows:
 *  - the product title
 *  - the product preset name
 *  - the deliveries the product is sent to
 *
 * These tests open the New Product dialog, fill minimal fields, pick the E2E product preset
 * (its channels come ticked), and click Publish — then assert the confirmation dialog content.
 */

const PUBLISH_URL = '/publish'

test.describe('Publish confirmation dialog', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto(PUBLISH_URL)
        await expect(page).toHaveURL(/\/publish/)
    })

    test('should show the product preset and its deliveries in the publish confirmation', async ({ page }) => {
        // Open the New Product dialog.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        const form = dialog.locator('.v-card-text').first()

        // Fill a unique title.
        const productTitle = generateTestName('E2E Publish Confirm')
        await form.locator('input').nth(1).fill(productTitle)

        // Pick the product preset 00-config-seed made; its channels come ticked.
        // Vuetify teleports the dropdown to body; scope to visible list items.
        const productPresetSelect = form.locator('.v-select').first()
        await productPresetSelect.click()
        const dropdownItems = page.locator('.v-overlay__content:visible .v-list-item')
        await dropdownItems
            .filter({ hasText: /E2E Product Preset/ })
            .first()
            .click()
        await expect(form.locator('.v-checkbox input').first()).toBeChecked()

        // Click Publish — this triggers handlePublishConfirmation. Because the form is dirty
        // (we just typed the title), it first opens the "Publish Unsaved Product" unsaved-changes
        // dialog (`showPublishUnsavedConfirmation`), NOT the ConfirmationDialog. We must click
        // "Save and Publish" to save the product first, which then opens the actual
        // ConfirmationDialog (showPublishConfirmation) showing the product title, product preset and
        // deliveries — the content this test asserts.
        await dialog.getByRole('button', { name: 'Publish product' }).click()

        // Unsaved-changes dialog ("Publish Unsaved Product") appears ON TOP OF the New Product
        // dialog. Both are .v-dialog.v-overlay--active — scope to the last (topmost) one.
        const unsavedDialog = page.locator('.v-dialog.v-overlay--active').last()
        await expect(unsavedDialog).toBeVisible({ timeout: 5000 })
        await expect(unsavedDialog).toContainText(/Publish Unsaved Product/i)

        // Click "Save and Publish" → saveAndPublish() saves the product, then opens
        // showPublishConfirmation (the ConfirmationDialog whose content we assert below).
        await unsavedDialog.getByRole('button', { name: /Save and Publish/i }).click()

        // The ConfirmationDialog appears ON TOP OF the now-saved New Product dialog (and the
        // unsaved-changes dialog has just closed). Scope by the unique publish-confirmation
        // marker so the Cancel-step assertion below tracks THIS dialog specifically rather
        // than re-evaluating `.last()` (which would resolve to the New Product dialog after
        // the confirmation closes, false-failing the `toHaveCount(0)` check).
        const confirmDialog = page.locator('.v-dialog.v-overlay--active').filter({
            hasText: /Do you really want to publish this product/i
        })
        await expect(confirmDialog).toBeVisible({ timeout: 5000 })

        // The confirmation should contain the product title.
        await expect(confirmDialog).toContainText(productTitle)

        // It should carry the product preset and deliveries labels
        // (product.publish_confirmation_product_preset / _deliveries).
        await expect(confirmDialog).toContainText(/Product: E2E Product Preset/i)
        await expect(confirmDialog).toContainText(/Sent to: .*E2E Publishing Channel/i)

        // Cancel — don't actually publish a throwaway product.
        await confirmDialog.getByRole('button', { name: 'Cancel' }).click()
        // After cancel only the New Product dialog remains; the confirmation overlay is gone.
        await expect(confirmDialog).toHaveCount(0)
    })

    test('should not render the Publish button before a product preset is chosen', async ({ page }) => {
        // Publish sends to the channels of the product's product preset; without one there is
        // nowhere to send, so the button is not rendered at all.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()

        await expect(dialog.getByRole('button', { name: 'Publish product' })).toHaveCount(0)

        await dialog.locator('.v-toolbar .v-btn').first().click()
    })
})
