import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getEntityTypeTags, type TagEntityType } from '@/api/tags'

/** A tag as reports and products use it: an admin tag, or a built-in one (`system_key` set). */
export type OfferedTag = {
    id: number
    display_name: string
    description: string | null
    color: string | null
    icon: string | null
    system_key: string | null
    sort_order: number
}

/**
 * The tags active for reports and for products, loaded once and shared by the cards, the tag
 * pickers and the filters. Configuration changes call `invalidate`, so the next use reloads.
 */
export const useTagsStore = defineStore('tags', () => {
    const offered = ref<Record<TagEntityType, OfferedTag[]>>({ report_item: [], product: [] })
    const pending: Partial<Record<TagEntityType, Promise<void>>> = {}

    function load(entityType: TagEntityType): Promise<void> {
        // Started inside a promise, so even a call that throws at once ends in the catch below.
        pending[entityType] ??= Promise.resolve()
            .then(() => getEntityTypeTags(entityType))
            .then((response) => {
                const tags = (response as { data?: { tags?: OfferedTag[] } }).data?.tags
                offered.value = { ...offered.value, [entityType]: Array.isArray(tags) ? tags : [] }
            })
            .catch((error: unknown) => {
                // Lists work without tags; the next use tries again.
                delete pending[entityType]
                console.error('Loading tags failed:', error)
            })
        return pending[entityType]
    }

    function invalidate(): void {
        delete pending.report_item
        delete pending.product
    }

    /** The tags people can put on an item, in their order. */
    const adminTags = (entityType: TagEntityType): OfferedTag[] => offered.value[entityType].filter((tag) => !tag.system_key)

    const byId = (entityType: TagEntityType, id: number): OfferedTag | undefined => offered.value[entityType].find((tag) => tag.id === id)

    /** A built-in tag, when it is active for the entity type. */
    const system = (entityType: TagEntityType, key: string): OfferedTag | undefined =>
        offered.value[entityType].find((tag) => tag.system_key === key)

    return { offered, load, invalidate, adminTags, byId, system }
})
