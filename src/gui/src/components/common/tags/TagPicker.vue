<template>
    <v-autocomplete
        :model-value="modelValue"
        :items="items"
        item-title="title"
        item-value="value"
        :label="label || t('tags.tags')"
        multiple
        chips
        closable-chips
        clear-on-select
        density="compact"
        variant="outlined"
        hide-details
        :disabled="disabled"
        :no-data-text="t('tags.none_defined')"
        data-test="tag-picker"
        @update:model-value="(value: number[]) => emit('update:modelValue', value)"
    >
        <template #chip="{ props: chipProps, item }">
            <v-chip
                v-bind="chipProps"
                :color="item.color || undefined"
                :prepend-icon="item.icon || undefined"
                label
                size="small"
            />
        </template>
    </v-autocomplete>
</template>

<script setup lang="ts">
    import { computed, onMounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import type { TagEntityType } from '@/api/tags'
    import { useTagLabels } from '@/composables/useTagLabels'
    import { useTagsStore } from '@/stores/tags'

    /** The tags people put on a report or product: the admin tags active for it, in their order. */

    const props = withDefaults(
        defineProps<{
            entityType: TagEntityType
            modelValue: number[]
            label?: string
            disabled?: boolean
        }>(),
        { label: '', disabled: false }
    )

    const emit = defineEmits<{ (e: 'update:modelValue', value: number[]): void }>()

    const { t } = useI18n()
    const tagsStore = useTagsStore()
    const { tagName } = useTagLabels()

    const items = computed(() =>
        tagsStore.adminTags(props.entityType).map((tag) => ({ title: tagName(tag), value: tag.id, color: tag.color, icon: tag.icon }))
    )

    onMounted(() => void tagsStore.load(props.entityType))
</script>
