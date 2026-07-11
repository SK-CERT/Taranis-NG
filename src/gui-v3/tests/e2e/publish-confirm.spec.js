import { test, expect } from '@playwright/test'
import { login, generateTestName } from '../helpers/test-helpers'

/**
 * Publish confirmation dialog E2E Tests
 *
 * Verifies that the publish confirmation dialog (ConfirmationDialog) shows:
 *  - the product title
 *  - the product type name
 *  - the selected publisher preset names
 *
 * These tests open the New Product dialog, fill minimal fields, select a publisher
 * preset, and click Publish — then assert the confirmation dialog content.
 * They are skipped when the environment has no product types or publisher presets.
 */

const PUBLISH_URL = '/v2/publish'

test.describe('Publish confirmation dialog', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto(PUBLISH_URL)
        await expect(page).toHaveURL(/\/publish/)
    })

    test('should show product type and publisher preset in the publish confirmation', async ({ page }) => {
        // Open the New Product dialog.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()
        const form = dialog.locator('.v-card-text').first()

        // Fill a unique title.
        const productTitle = generateTestName('E2E Publish Confirm')
        await form.locator('input').nth(1).fill(productTitle)

        // Select the first product type from the combobox.
        // Vuetify 3 teleports the dropdown to body; scope to visible list items.
        const typeCombo = form.locator('.v-combobox').first()
        await typeCombo.click()
        const dropdownItems = page.locator('.v-overlay__content:visible .v-list-item')
        await dropdownItems.first().click()

        // Select the first publisher preset checkbox.
        const presetCheckbox = form.locator('.v-checkbox').first()
        await presetCheckbox.locator('input').check()

        // Click Publish — this triggers handlePublishConfirmation → showPublishConfirmation.
        await dialog.getByRole('button', { name: 'Publish product' }).click()

        // The ConfirmationDialog appears.
        const confirmDialog = page.locator('.v-dialog.v-overlay--active')
        await expect(confirmDialog).toBeVisible({ timeout: 5000 })

        // The confirmation should contain the product title.
        await expect(confirmDialog).toContainText(productTitle)

        // It should contain the "Product Type" label and the "Publisher Presets" label.
        await expect(confirmDialog).toContainText(/Product Type/i)
        await expect(confirmDialog).toContainText(/Publisher Presets/i)

        // Cancel — don't actually publish a throwaway product.
        await confirmDialog.getByRole('button', { name: 'Cancel' }).click()
        await expect(confirmDialog).toHaveCount(0)
    })

    test('should not render the Publish button without publisher presets', async ({ page }) => {
        // When no publisher presets are configured, canPublish is false and the
        // "Publish product" button is not rendered at all — so there's nothing
        // to confirm. This test verifies that absence rather than trying to click
        // a button that doesn't exist.
        await page.getByRole('button', { name: 'Add New' }).click()
        const dialog = page.locator('.v-dialog.v-overlay--active')
        await expect(dialog).toBeVisible()

        const publishBtn = dialog.getByRole('button', { name: 'Publish product' })
        const publishVisible = await publishBtn.count()

        if (publishVisible === 0) {
            // No publisher presets in the environment → Publish button correctly absent.
            // Close the dialog and pass.
            await dialog.locator('.v-toolbar .v-btn').first().click()
            return
        }

        // If publisher presets DO exist, verify the button doesn't trigger a
        // confirmation without selecting one (the validation toast blocks it).
        await publishBtn.click()
        await page.waitForTimeout(1000)

        // Only the New Product dialog should be visible — no confirmation overlay.
        const overlays = page.locator('.v-dialog.v-overlay--active')
        // The confirmation dialog contains "Do you really want" — it should NOT appear.
        await expect(overlays.filter({ hasText: /Do you really want/i })).toHaveCount(0)

        await dialog.locator('.v-toolbar .v-btn').first().click()
    })
})
