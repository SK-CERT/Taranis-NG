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
        // The toolbar itself, not the empty-state heading. That heading reads "No news items
        // found", so matching /news items/i on it asserted the opposite of what this test is
        // named for: it passed only while the instance held no news at all, and any spec that
        // collected something - creating a source now collects it at once - broke this one.
        await expect(page.locator('.toolbar-filter__search input').first()).toBeVisible()
    })

    test('should accept input in the search field', async ({ page }) => {
        // The toolbar is BaseToolbarFilter's own `section.toolbar-filter`, not a `v-toolbar`.
        const search = page.locator('.toolbar-filter__search input').first()
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

        // The active range chip switches to the tonal primary variant
        // (`:color="primary" :variant="tonal"` in BaseToolbarFilter). Vuetify renders a
        // tonal chip with `text-primary`; only flat/elevated variants get `bg-primary`.
        await expect(todayChip).toHaveClass(/v-chip--variant-tonal/)
        await expect(todayChip).toHaveClass(/text-primary/)
    })

    test('should show the three-state filter chips (read / important / relevant)', async ({ page }) => {
        // The custom-filters slot renders three clickable icon chips.
        const filterChips = page.locator('.toolbar-filter__custom .v-chip')
        await expect(filterChips.first()).toBeVisible()
        expect(await filterChips.count()).toBeGreaterThanOrEqual(3)
    })

    test('should expose toolbar action tooltips as native title attributes', async ({ page }) => {
        // The toolbar buttons use native `title` tooltips (consistent app-wide).
        await expect(page.getByTitle('Toggle compact mode')).toBeVisible()
        await expect(page.getByTitle('Toggle news items selection mode')).toBeVisible()
    })

    test('should reveal selection actions after entering multi-select mode', async ({ page }) => {
        const selectAll = page.getByTitle('Select All')
        // Select All keeps its place in the toolbar at all times so the row does not change
        // shape, but stays inactive until selection mode is on. The actions that need an actual
        // selection are the ones that appear.
        await expect(selectAll).toBeDisabled()
        await expect(page.getByTitle('Mark news items as read')).toHaveCount(0)

        await page.getByTitle('Toggle news items selection mode').click()

        await expect(selectAll).toBeEnabled()
        await expect(page.getByTitle('Mark news items as read')).toBeVisible()
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
