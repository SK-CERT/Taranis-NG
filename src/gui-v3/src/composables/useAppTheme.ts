import { ref } from 'vue'
import { useTheme } from 'vuetify'
import { DEFAULT_THEME_FAMILY, resolveFamily, themeName } from '@/themes'
import { Settings } from '@/types/settings'

const FAMILY_STORAGE_KEY = 'taranis-theme-family'

/**
 * Remembering the family locally is what keeps the login page - and the first
 * paint after a reload, before the user's settings come back from the API - on
 * the theme the user actually picked instead of flashing the default one.
 */
const readStoredFamily = (): string => {
    try {
        return resolveFamily(localStorage.getItem(FAMILY_STORAGE_KEY))
    } catch {
        return DEFAULT_THEME_FAMILY
    }
}

const storeFamily = (family: string): void => {
    try {
        localStorage.setItem(FAMILY_STORAGE_KEY, family)
    } catch {
        // Private mode / blocked storage: the family simply is not remembered.
    }
}

// Module scope: every caller shares one view of the active theme.
const family = ref<string>(readStoredFamily())
const isDark = ref<boolean>(false)

type SettingsSource = {
    getSetting: (key: string, defValue?: string) => string
    getSettingBoolean: (key: string, defValue?: boolean) => boolean
}

export function useAppTheme() {
    const theme = useTheme()

    const apply = (nextFamily: string, dark: boolean): void => {
        family.value = resolveFamily(nextFamily)
        isDark.value = dark
        storeFamily(family.value)

        const name = themeName(family.value, dark)
        if (typeof theme.change === 'function') {
            theme.change(name)
        } else {
            // Vuetify exposes change() from v3.9; keep the assignment fallback.
            theme.global.name.value = name
        }
    }

    /** Switch variant, keep the family. */
    const applyVariant = (dark: boolean): void => apply(family.value, dark)

    /** Switch family, keep the variant. */
    const applyFamily = (nextFamily: string): void => apply(nextFamily, isDark.value)

    /** Authoritative once the user's settings have loaded. */
    const applyFromSettings = (settings: SettingsSource): void => {
        apply(
            resolveFamily(settings.getSetting(Settings.UI_THEME, DEFAULT_THEME_FAMILY)),
            settings.getSettingBoolean(Settings.DARK_THEME, false)
        )
    }

    /**
     * Pre-login and post-logout: the family is whatever was last used on this
     * device, the variant follows the OS. Vuetify's built-in 'system' theme
     * cannot be used for this - it resolves to the built-in light/dark themes
     * and so cannot select a family variant.
     */
    const applyBrowserVariant = (): void => apply(family.value, window.matchMedia('(prefers-color-scheme: dark)').matches)

    return { family, isDark, apply, applyVariant, applyFamily, applyFromSettings, applyBrowserVariant }
}
