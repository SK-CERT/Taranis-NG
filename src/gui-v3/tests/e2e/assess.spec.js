import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'

/**
 * Assess E2E Tests
 *
 * Exercises the Assess view toolbar: title, search, day-range filters, the
 * three-state filter chips, the native-title tooltips, and multi-select mode.
 * These assertions target the toolbar (always rendered) so they don't depend on
 * news-item data being present in the environment.
 */

test.describe('Assess', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
        await page.goto('/v2/assess')
        await expect(page).toHaveURL(/\/assess/)
    })

    test('should load the Assess view with the News Items toolbar', async ({ page }) => {
        await expect(
            page
                .locator('.text-h6')
                .filter({ hasText: /news items/i })
                .first()
        ).toBeVisible()
    })

    test('should accept input in the search field', async ({ page }) => {
        const search = page.locator('.v-toolbar .v-text-field input').first()
        await expect(search).toBeVisible()

        await search.fill('apt')
        await expect(search).toHaveValue('apt')
    })

    test('should activate a day-range filter chip when clicked', async ({ page }) => {
        const todayChip = page
            .locator('.v-chip')
            .filter({ hasText: /^Today$/ })
            .first()
        await expect(todayChip).toBeVisible()

        await todayChip.click()

        // Active range chip switches to the filled primary variant.
        await expect(todayChip).toHaveClass(/bg-primary/)
    })

    test('should show the three-state filter chips (read / important / relevant)', async ({ page }) => {
        // The custom-filters slot renders three clickable icon chips.
        const filterChips = page.locator('.v-toolbar .v-chip')
        await expect(filterChips.first()).toBeVisible()
        expect(await filterChips.count()).toBeGreaterThanOrEqual(3)
    })

    test('should expose toolbar action tooltips as native title attributes', async ({ page }) => {
        // The toolbar buttons use native `title` tooltips (consistent app-wide).
        await expect(page.getByTitle('Toggle compact mode')).toBeVisible()
        await expect(page.getByTitle('Toggle news items selection mode')).toBeVisible()
    })

    test('should reveal selection actions after entering multi-select mode', async ({ page }) => {
        // Select-all only exists once multi-select is enabled.
        await expect(page.getByTitle('Select All')).toHaveCount(0)

        await page.getByTitle('Toggle news items selection mode').click()

        await expect(page.getByTitle('Select All')).toBeVisible()
    })

    test('should toggle compact mode without errors', async ({ page }) => {
        const compactBtn = page.getByTitle('Toggle compact mode')
        await expect(compactBtn).toBeVisible()

        await compactBtn.click()
        // Still on the Assess view and the toolbar remains interactive.
        await expect(page).toHaveURL(/\/assess/)
        await expect(compactBtn).toBeVisible()
    })
})
