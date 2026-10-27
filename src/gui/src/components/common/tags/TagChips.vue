<template>
    <span
        v-if="adminTags.length > 0 || statusChips.length > 0"
        class="tag-chips d-inline-flex flex-wrap align-center ga-1"
        data-test="tag-chips"
    >
        <v-chip
            v-for="tag in adminTags"
            :key="`tag-${tag.id}`"
            :color="tag.color || undefined"
            :prepend-icon="tag.icon || undefined"
            :size="size"
            :title="tag.description || tagName(tag)"
            label
            variant="flat"
            data-test="tag-chip"
        >
            <bdi dir="auto">{{ tagName(tag) }}</bdi>
        </v-chip>
        <v-chip
            v-for="chip in statusChips"
            :key="`status-${chip.language}`"
            :color="chip.tag.color || undefined"
            :prepend-icon="chip.tag.icon || undefined"
            :size="size"
            :title="chip.title"
            label
            variant="tonal"
            :data-test="`translation-status-${chip.language || 'none'}`"
        >
            {{ chip.text }}
        </v-chip>
    </span>
</template>

<script setup lang="ts">
    import { computed, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import type { TagEntityType } from '@/api/tags'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import { useTagLabels } from '@/composables/useTagLabels'
    import { useTagsStore, type OfferedTag } from '@/stores/tags'

    /**
     * The tags of a report or product: the ones people put on it, then its translation status per
     * language - a chip per language code styled with that status's built-in tag - or "language
     * not set". Tags switched off in Tag Workflow are not shown.
     */

    const props = withDefaults(
        defineProps<{
            entityType: TagEntityType
            tagIds?: number[] | undefined
            // Language -> built-in tag key, "" for an item whose language is not set.
            translationStatus?: Record<string, string> | undefined
            size?: 'x-small' | 'small' | 'default'
        }>(),
        { tagIds: () => [], translationStatus: () => ({}), size: 'x-small' }
    )

    const { t } = useI18n()
    const tagsStore = useTagsStore()
    const { tagName } = useTagLabels()
    const { languageName } = useContentLanguages()

    const adminTags = computed<OfferedTag[]>(() =>
        tagsStore.adminTags(props.entityType).filter((tag) => (props.tagIds ?? []).includes(tag.id))
    )

    const statusChips = computed(() =>
        Object.entries(props.translationStatus ?? {}).flatMap(([language, key]) => {
            const tag = tagsStore.system(props.entityType, key)
            if (!tag) return []
            const status = tagName(tag)
            return [
                {
                    language,
                    tag,
                    text: language ? language.toUpperCase() : status,
                    title: language ? t('tags.status_in_language', { language: languageName(language), status }) : status
                }
            ]
        })
    )

    onMounted(() => void tagsStore.load(props.entityType))
</script>
