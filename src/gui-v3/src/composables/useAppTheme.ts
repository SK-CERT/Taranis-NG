import { ref } from 'vue'
import { useTheme } from 'vuetify'
import { buildVariant, DEFAULT_THEME_FAMILY, getFamily, resolveFamily, themeName, type BuiltVariant } from '@/themes'
import { CUSTOM_THEME_FAMILY, parseCustomTheme, readBasedOn, seedFromFamily, toThemeFamily, type CustomThemeData } from '@/themes/custom'
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

    /**
     * Write a user's palette into the live Vuetify themes. `theme.themes` is
     * documented as mutable for exactly this - the registry itself is a
     * build-time constant, so a runtime theme cannot go through it.
     */
    const installCustomTheme = (data: CustomThemeData): void => {
        const family = toThemeFamily(data)

        // `themes` holds the raw definitions; `computedThemes` derives the on-*
        // colours from them. Its type describes the computed shape, so a raw
        // definition - which deliberately omits the colours Vuetify works out
        // itself - needs the cast.
        const themes = theme.themes.value as unknown as Record<string, BuiltVariant>
        themes[themeName(CUSTOM_THEME_FAMILY, false)] = buildVariant(family.light, false)
        themes[themeName(CUSTOM_THEME_FAMILY, true)] = buildVariant(family.dark, true)
    }

    /** The seed a fresh custom theme starts from: whatever family is active now. */
    const customThemeSeed = (basedOn?: string): CustomThemeData => {
        const source = resolveFamily(basedOn) === CUSTOM_THEME_FAMILY ? DEFAULT_THEME_FAMILY : resolveFamily(basedOn)

        return { basedOn: source, ...seedFromFamily(getFamily(source)) }
    }

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
        const nextFamily = resolveFamily(settings.getSetting(Settings.UI_THEME, DEFAULT_THEME_FAMILY))

        // Install the saved palette before switching, so the first paint is
        // already the user's colours rather than the baked-in placeholder.
        if (nextFamily === CUSTOM_THEME_FAMILY) {
            const stored = settings.getSetting(Settings.CUSTOM_THEME, '')
            installCustomTheme(parseCustomTheme(stored, customThemeSeed(readBasedOn(stored))))
        }

        apply(nextFamily, settings.getSettingBoolean(Settings.DARK_THEME, false))
    }

    /**
     * Show a variant without claiming it as the user's choice. The theme editor
     * previews the variant it is editing; DARK_THEME stays untouched.
     */
    const previewVariant = (dark: boolean): void => {
        const name = themeName(family.value, dark)
        if (typeof theme.change === 'function') theme.change(name)
        else theme.global.name.value = name
    }

    /**
     * Pre-login and post-logout: the family is whatever was last used on this
     * device, the variant follows the OS. Vuetify's built-in 'system' theme
     * cannot be used for this - it resolves to the built-in light/dark themes
     * and so cannot select a family variant.
     */
    const applyBrowserVariant = (): void => apply(family.value, window.matchMedia('(prefers-color-scheme: dark)').matches)

    return {
        family,
        isDark,
        apply,
        applyVariant,
        applyFamily,
        applyFromSettings,
        applyBrowserVariant,
        installCustomTheme,
        customThemeSeed,
        previewVariant
    }
}
