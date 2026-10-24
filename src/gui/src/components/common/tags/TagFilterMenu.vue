<template>
    <v-menu
        v-model="open"
        :close-on-content-click="false"
        location="bottom"
    >
        <template #activator="{ props: menuProps }">
            <v-chip
                v-bind="menuProps"
                size="small"
                :color="active ? 'primary' : 'default'"
                :variant="active ? 'flat' : 'outlined'"
                :title="t('tags.filter')"
                data-test="tag-filter"
            >
                <v-icon>mdi-tag-multiple-outline</v-icon>
                <span
                    v-if="activeCount > 0"
                    class="ms-1"
                    >{{ activeCount }}</span
                >
            </v-chip>
        </template>
        <v-card
            min-width="320"
            data-test="tag-filter-menu"
        >
            <v-card-text class="d-flex flex-column ga-3">
                <v-select
                    v-if="adminTags.length > 0"
                    :model-value="modelValue.tags ?? []"
                    :items="adminTags"
                    :label="t('tags.tags')"
                    multiple
                    chips
                    closable-chips
                    density="compact"
                    variant="outlined"
                    hide-details
                    data-test="filter-tags"
                    @update:model-value="(tags: number[]) => update({ tags })"
                />
                <v-select
                    :model-value="modelValue.translation ?? ''"
                    :items="translationItems"
                    :label="t('tags.translation')"
                    density="compact"
                    variant="outlined"
                    hide-details
                    data-test="filter-translation"
                    @update:model-value="(translation: TranslationFilter) => update({ translation })"
                />
                <v-autocomplete
                    v-if="modelValue.translation === 'needs' || modelValue.translation === 'unreviewed'"
                    :model-value="modelValue.translation_language ?? null"
                    :items="languageOptions"
                    item-title="txt"
                    item-value="id"
                    :label="t('tags.translation_language')"
                    density="compact"
                    variant="outlined"
                    hide-details
                    dir="auto"
                    data-test="filter-translation-language"
                    @update:model-value="(translation_language: string | null) => update({ translation_language })"
                />
            </v-card-text>
            <v-card-actions>
                <v-spacer />
                <v-btn
                    variant="text"
                    :disabled="!active"
                    @click="update({ tags: [], translation: '', translation_language: null })"
                >
                    {{ t('tags.clear_filter') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-menu>
</template>

<script setup lang="ts">
    import { computed, onMounted, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import type { TagEntityType, TagFilterState, TranslationFilter } from '@/api/tags'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import { useTagLabels } from '@/composables/useTagLabels'
    import { useTagsStore } from '@/stores/tags'

    /**
     * The tag and translation filters of a list (Analyze, Publish): items with any of the chosen
     * tags, and items needing a translation into a language, with an AI translation nobody
     * reviewed, or with no language set.
     */

    const props = defineProps<{ entityType: TagEntityType; modelValue: TagFilterState }>()
    const emit = defineEmits<{ (e: 'update:modelValue', value: TagFilterState): void }>()

    const { t } = useI18n()
    const tagsStore = useTagsStore()
    const { tagName } = useTagLabels()
    const { languageOptions } = useContentLanguages()
    const open = ref(false)

    const adminTags = computed(() => tagsStore.adminTags(props.entityType).map((tag) => ({ title: tagName(tag), value: tag.id })))
    const translationItems = computed(() => [
        { title: t('tags.translation_any'), value: '' },
        { title: t('tags.translation_needs'), value: 'needs' },
        { title: t('tags.translation_unreviewed'), value: 'unreviewed' },
        { title: t('tags.translation_not_set'), value: 'not_set' }
    ])

    // A translation filter counts once it can be applied (a language chosen, or "not set").
    const translationActive = computed(
        () => props.modelValue.translation === 'not_set' || Boolean(props.modelValue.translation && props.modelValue.translation_language)
    )
    const activeCount = computed(() => (props.modelValue.tags?.length ?? 0) + (translationActive.value ? 1 : 0))
    const active = computed(() => activeCount.value > 0)

    const update = (change: Partial<TagFilterState>): void => {
        emit('update:modelValue', { ...props.modelValue, ...change })
    }

    onMounted(() => void tagsStore.load(props.entityType))
</script>
