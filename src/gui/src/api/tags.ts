import ApiService from '@/services/api_service'

export type TagEntityType = 'report_item' | 'product'

/** The tags active for reports or products, in their Tag Workflow order, the built-in ones included. */
export function getEntityTypeTags(entityType: TagEntityType) {
    return ApiService.get(`/tags/entity-types/${entityType}`)
}

export type TranslationFilter = '' | 'needs' | 'unreviewed' | 'not_set'

export type TagFilterState = {
    // Admin tag ids; an item with any of them is listed.
    tags?: number[]
    translation?: TranslationFilter
    translation_language?: string | null
}

/** The tag and translation filters of a list request, as a query string fragment (`&tags=...`). */
export function tagFilterQuery(filter: TagFilterState): string {
    let query = ''
    if (filter.tags && filter.tags.length > 0) {
        query += '&tags=' + encodeURIComponent(filter.tags.join(','))
    }
    if (filter.translation === 'not_set') {
        query += '&translation=not_set'
    } else if (filter.translation && filter.translation_language) {
        query += '&translation=' + encodeURIComponent(filter.translation)
        query += '&translation_language=' + encodeURIComponent(filter.translation_language)
    }
    return query
}
