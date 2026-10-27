<template>
    <div
        v-if="languages.length > 0"
        class="d-flex align-center flex-wrap ga-2 mb-3"
        data-test="product-languages"
    >
        <v-tabs
            :model-value="modelValue"
            density="compact"
            data-test="product-language-tabs"
            @update:model-value="(value: unknown) => emit('update:modelValue', String(value))"
        >
            <v-tab value="source">{{ sourceLabel }}</v-tab>
            <v-tab
                v-for="code in languages"
                :key="code"
                :value="code"
                :disabled="!language"
            >
                <TranslationStatusIcon
                    entity-type="product"
                    :status="statuses[code]"
                    class="me-1"
                />
                {{ languageName(code) }}
            </v-tab>
        </v-tabs>
        <v-spacer />
        <v-btn
            v-if="canModify && language"
            color="primary"
            variant="tonal"
            prepend-icon="mdi-translate"
            :loading="translating"
            :disabled="translating"
            data-test="translate-product"
            @click="emit('translate-all')"
        >
            {{ t('product.translate_product') }}
        </v-btn>
    </div>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import TranslationStatusIcon from '@/components/common/tags/TranslationStatusIcon.vue'
    import { useContentLanguages } from '@/composables/useContentLanguages'

    /**
     * A product's languages as tabs: the one it is written in (chosen in the dialog's toolbar),
     * and those of its reports' types. The open tab is the language the product is previewed,
     * downloaded and published in.
     */

    const props = withDefaults(
        defineProps<{
            modelValue: string
            language: string | null
            languages: string[]
            // The title's translation status per language (built-in tag keys).
            statuses?: Record<string, string>
            canModify?: boolean
            translating?: boolean
        }>(),
        { statuses: () => ({}), canModify: false, translating: false }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: string): void
        (e: 'translate-all'): void
    }>()

    const { t } = useI18n()
    const { languageName } = useContentLanguages()

    const sourceLabel = computed(() =>
        props.language
            ? t('report_item.translation.source_tab', { language: languageName(props.language) })
            : t('report_item.translation.source_not_set')
    )
</script>
