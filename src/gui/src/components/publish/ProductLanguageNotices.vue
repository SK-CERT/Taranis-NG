<template>
    <div
        v-if="check && language"
        data-test="product-language-notices"
    >
        <!-- Per format of the product preset: templates known to be in another language (e.g.
             "e-mail CZ" for Slovak) warn; default templates whose language is not set only inform.
             The format is named when the product preset has several. -->
        <v-alert
            v-for="format in check.formats.filter((entry) => entry.template_language !== language)"
            :key="format.product_format_id"
            :type="format.template_language ? 'warning' : 'info'"
            variant="tonal"
            density="compact"
            class="mb-2"
            data-test="notice-templates"
        >
            <template v-if="check.formats.length > 1">
                <bdi
                    dir="auto"
                    class="font-weight-medium"
                    >{{ format.title }}</bdi
                >:
            </template>
            {{
                t('product.language_notice.templates', {
                    language: languageName(language),
                    used: format.template_language ? languageName(format.template_language) : t('product.language_notice.default_templates')
                })
            }}
        </v-alert>
        <v-alert
            v-if="check.missing.length > 0"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-2"
            data-test="notice-missing"
        >
            {{ t('product.language_notice.missing', { language: languageName(language), count: check.missing.length }) }}
            <bdi dir="auto">{{ formatList(check.missing.map((report) => report.title)) }}</bdi>
        </v-alert>
        <v-alert
            v-if="check.outdated.length > 0"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-2"
            data-test="notice-outdated"
        >
            {{ t('product.language_notice.outdated', { language: languageName(language) }) }}
            <ul class="ms-4">
                <li
                    v-for="(entry, index) in check.outdated"
                    :key="index"
                >
                    <bdi dir="auto">{{ entry.title }}</bdi> — <bdi dir="auto">{{ fieldName(entry.field) }}</bdi>
                </li>
            </ul>
        </v-alert>
    </div>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { useContentLanguages } from '@/composables/useContentLanguages'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'

    /** What rendering the product in a language falls back on (from core's language check). */

    export type LanguageCheck = {
        missing: Array<{ id: number; title: string }>
        outdated: Array<{ report_item_id: number; title: string; field: string }>
        /** The language of the templates each format of the product preset renders it with. */
        formats: Array<{ product_format_id: number; title: string; template_language: string | null }>
    }

    defineProps<{
        check: LanguageCheck | null
        language: string | null
    }>()

    const { t } = useI18n()
    const { languageName } = useContentLanguages()
    const { formatList: formatLocaleList } = useLocaleFormatters()

    const formatList = (items: string[]): string => formatLocaleList(items, { style: 'long', type: 'conjunction' })

    const fieldName = (field: string): string => {
        if (field === 'title') return t('report_item.title')
        if (field === 'title_prefix') return t('report_item.title_prefix')
        return field
    }
</script>
