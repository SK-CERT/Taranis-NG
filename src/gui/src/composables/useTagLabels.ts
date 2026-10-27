import { useI18n } from 'vue-i18n'
import type { OfferedTag } from '@/stores/tags'

/**
 * A tag's name for people. A built-in tag is named by its key, translated
 * (`workflow.tags.system.<key>`), the way system states are shown; one renamed before built-in
 * names were locked keeps that name until it is saved again.
 */
export function useTagLabels() {
    const { t, te } = useI18n()

    const tagName = (tag: Pick<OfferedTag, 'display_name' | 'system_key'> | null | undefined): string => {
        if (!tag) return ''
        const key = `workflow.tags.system.${tag.display_name}`
        return tag.system_key && tag.display_name === tag.system_key && te(key) ? t(key) : tag.display_name
    }

    return { tagName }
}
