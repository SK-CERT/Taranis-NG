import { computed, type ComputedRef } from 'vue'
import { useTheme } from 'vuetify'
import { useSettingsStore } from '@/stores/settings'
import { Settings } from '@/types/settings'
import { tagPalette } from '@/themes/tagPalette'

/**
 * The tag cloud's colours for the theme that is currently applied.
 *
 * It reads the resolved Vuetify theme rather than the static registry, so it
 * follows a live theme change - including edits made in the theme editor,
 * which write straight into `theme.themes`.
 *
 * The existing per-user TAG_COLOR setting ("Colorful tag cloud") chooses
 * between the four identity colours and a single hue. Colour on the cloud
 * encodes nothing - font size already carries frequency - so being able to
 * turn the decoration off is the honest default behaviour.
 */
export function useTagPalette(): ComputedRef<string[]> {
    const theme = useTheme()
    const settingsStore = useSettingsStore()

    return computed(() => {
        const current = theme.current.value
        const colors = (current.colors ?? {}) as Record<string, string>
        const ground = colors['surface'] ?? (current.dark ? '#000000' : '#FFFFFF')
        // Defaults to false, matching how TAG_COLOR is seeded and how the legacy
        // GUI reads it.
        const colorful = settingsStore.getSettingBoolean(Settings.TAG_COLOR, false)

        return tagPalette(colors, ground, Boolean(current.dark), colorful)
    })
}
