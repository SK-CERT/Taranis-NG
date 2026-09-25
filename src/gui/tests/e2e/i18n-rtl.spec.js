import { test, expect } from '@playwright/test'
import { login } from '../helpers/test-helpers'

const SETTINGS_ENDPOINT = '/api/v1/config/settings?search='

// The core authenticates with a Bearer token that the app keeps in localStorage
// (see services/api_service.ts). `page.request` shares the browser's cookies but NOT
// axios' default headers, so every direct API call here has to attach the token itself
// — without it the config endpoints answer 401.
const authHeaders = async (page) => {
    const token = await page.evaluate(() => localStorage.getItem('ACCESS_TOKEN'))
    expect(token, 'no ACCESS_TOKEN in localStorage — is the session still logged in?').toBeTruthy()
    return { Authorization: `Bearer ${token}` }
}

const loadUiLanguageSetting = async (page) => {
    const response = await page.request.get(SETTINGS_ENDPOINT, { headers: await authHeaders(page) })
    expect(response.ok(), `GET ${SETTINGS_ENDPOINT} failed: ${response.status()}`).toBe(true)
    const settings = await response.json()
    const uiLanguage = settings.find((setting) => setting.key === 'UI_LANGUAGE')
    expect(uiLanguage).toBeTruthy()
    return uiLanguage
}

const saveUiLanguage = async (page, value) => {
    // Reload before every write: the first personal override creates a settings_user
    // record, so reusing the earlier null user_setting_id would attempt a duplicate
    // insert during cleanup instead of updating the record just created by the test.
    const currentSetting = await loadUiLanguageSetting(page)
    const response = await page.request.put(`/api/v1/config/user-settings/${currentSetting.id}`, {
        headers: await authHeaders(page),
        data: { ...currentSetting, value }
    })
    expect(response.ok(), `PUT user-settings failed: ${response.status()}`).toBe(true)
}

test.describe('Arabic production locale', () => {
    test('selects, persists, and restores Arabic through user settings', async ({ page }) => {
        await login(page)
        const originalSetting = await loadUiLanguageSetting(page)
        const originalLocale = originalSetting.value

        try {
            // The runtime-switch assertions need a known LTR starting point. Preserve and
            // restore the user's actual value even if a previous interrupted run left Arabic.
            if (originalLocale !== 'en') {
                await saveUiLanguage(page, 'en')
                await page.reload()
                await expect(page.locator('html')).toHaveAttribute('lang', 'en')
                await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
            }

            await page.locator('[data-test="user-menu"]').click()
            await page.getByText('Settings', { exact: true }).click()

            const dialog = page.locator('.user-settings-dialog')
            await expect(dialog).toBeVisible()
            const languageRow = dialog.locator('.settings-table--personal tbody tr').filter({ hasText: 'User interface language' })
            const languageSelect = languageRow.locator('.v-select')
            await expect(languageSelect).toBeVisible()

            const updateResponse = page.waitForResponse(
                (response) => response.request().method() === 'PUT' && /\/api\/v1\/config\/user-settings\/\d+$/.test(response.url())
            )
            await languageSelect.click()
            await page.locator('.v-overlay__content:visible .v-list-item').filter({ hasText: 'العربية' }).click()
            expect((await updateResponse).ok()).toBe(true)

            await expect(page.locator('html')).toHaveAttribute('lang', 'ar')
            await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
            await expect(page.locator('.v-locale--is-rtl').first()).toBeVisible()

            // Reload proves the personal setting was persisted by the selection's auto-save,
            // rather than only changing the in-memory vue-i18n locale.
            await page.reload()
            await expect(page.locator('html')).toHaveAttribute('lang', 'ar')
            await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
            await expect(page.locator('.v-locale--is-rtl').first()).toBeVisible()
        } finally {
            await saveUiLanguage(page, originalLocale)
            await page.reload()
            expect((await loadUiLanguageSetting(page)).value).toBe(originalLocale)
        }
    })
})
