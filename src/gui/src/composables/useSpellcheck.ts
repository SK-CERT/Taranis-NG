import { computed, type ComputedRef } from 'vue'
import { useSettingsStore } from '@/stores/settings'

/** Browser spellchecking for natural-language inputs, controlled by the user setting. */
export function useSpellcheck(): ComputedRef<boolean> {
    const settingsStore = useSettingsStore()
    return computed(() => settingsStore.spellcheck)
}
