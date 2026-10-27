<template>
    <v-autocomplete
        :model-value="modelValue"
        :items="languageOptions"
        item-title="txt"
        item-value="id"
        dir="auto"
        :label="label"
        :placeholder="t('report_item.translation.not_set')"
        persistent-placeholder
        density="compact"
        variant="outlined"
        hide-details
        style="max-width: 220px"
        :disabled="disabled"
        @update:model-value="(value: string | null) => value && emit('update:modelValue', value)"
    />
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useContentLanguages } from '@/composables/useContentLanguages'

    /**
     * The language a report or product is written in, for its dialog's toolbar beside the state.
     * A language not set yet shows as such; once set, it can be changed but not cleared.
     */

    withDefaults(
        defineProps<{
            modelValue: string | null
            label: string
            disabled?: boolean
        }>(),
        { disabled: false }
    )

    const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

    const { t } = useI18n()
    const { languageOptions } = useContentLanguages()
</script>
