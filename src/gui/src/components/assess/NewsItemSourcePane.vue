<template>
    <div class="source-tab">
        <!-- One revision of a news item as collected: pinned metadata header, scrolling body,
             pinned link footer. Used for the single Source tab, and for each version tab of a
             versioned item. Kept inside the root, so the component stays single-root and the
             dialog's pane classes fall through to it. -->
        <!-- Fixed header: metadata + article title stay pinned -->
        <div class="source-header">
            <v-row class="mb-6">
                <v-col
                    cols="12"
                    md="3"
                    class="text-center"
                >
                    <i18n-t
                        scope="global"
                        keypath="card_item.collected_at"
                        tag="div"
                        class="text-overline font-weight-bold"
                    >
                        <template #date>
                            <div class="text-caption font-weight-regular text-none">
                                <bdi dir="auto">{{ collectedDisplay }}</bdi>
                            </div>
                        </template>
                    </i18n-t>
                </v-col>
                <v-col
                    cols="12"
                    md="3"
                    class="text-center"
                >
                    <i18n-t
                        scope="global"
                        keypath="card_item.published_at"
                        tag="div"
                        class="text-overline font-weight-bold"
                    >
                        <template #date>
                            <div class="text-caption font-weight-regular text-none">
                                <bdi dir="auto">{{ publishedDisplay }}</bdi>
                            </div>
                        </template>
                    </i18n-t>
                </v-col>
                <v-col
                    cols="12"
                    md="3"
                    class="text-center"
                >
                    <i18n-t
                        scope="global"
                        keypath="card_item.source_with_value"
                        tag="div"
                        class="text-overline font-weight-bold"
                    >
                        <template #source>
                            <div class="text-caption font-weight-regular text-none">
                                <bdi dir="auto">{{ sourceDisplay }}</bdi>
                            </div>
                        </template>
                    </i18n-t>
                </v-col>
                <v-col
                    cols="12"
                    md="3"
                    class="text-center"
                >
                    <i18n-t
                        scope="global"
                        keypath="card_item.author_with_value"
                        tag="div"
                        class="text-overline font-weight-bold"
                    >
                        <template #author>
                            <div class="text-caption font-weight-regular text-none">
                                <bdi dir="auto">{{ authorDisplay }}</bdi>
                            </div>
                        </template>
                    </i18n-t>
                </v-col>
            </v-row>

            <!-- An older version says when a newer one replaced it -->
            <i18n-t
                v-if="superseded"
                scope="global"
                keypath="assess.superseded_at"
                tag="div"
                class="text-caption text-medium-emphasis mb-3 superseded-notice"
                data-test="superseded-notice"
            >
                <template #date>
                    <bdi dir="auto">{{ supersededDisplay }}</bdi>
                </template>
            </i18n-t>

            <v-divider />
        </div>

        <!-- Scrollable body: only the article content scrolls -->
        <div class="source-body">
            <div
                class="text-body-2 text-medium-emphasis"
                v-html="sanitizedContent"
            />
        </div>

        <!-- Fixed footer: link stays pinned -->
        <div
            v-if="link"
            class="source-footer"
        >
            <v-divider class="mb-3" />
            <div class="text-caption">
                <i18n-t
                    scope="global"
                    keypath="card_item.link_with_url"
                >
                    <template #url>
                        <a
                            v-if="isSafeLink"
                            :href="link"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            <bdi dir="ltr">{{ link }}</bdi>
                        </a>
                        <bdi
                            v-else
                            dir="ltr"
                            >{{ link }}</bdi
                        >
                    </template>
                </i18n-t>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { sanitizeNewsItemHtml } from '@/utils/sanitizeNewsItemHtml'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'

    const props = withDefaults(
        defineProps<{
            collected?: string | null | undefined
            published?: string | null | undefined
            source?: string | null | undefined
            author?: string | null | undefined
            content?: string | null | undefined
            link?: string | null | undefined
            /** When a newer version replaced this one; set only for older versions. */
            superseded?: string | null | undefined
        }>(),
        {
            collected: null,
            published: null,
            source: null,
            author: null,
            content: null,
            link: null,
            superseded: null
        }
    )

    const { t } = useI18n()
    const { formatDateTime } = useLocaleFormatters()

    const formatMetadataDate = (value: unknown): string => {
        if (value === null || value === undefined || value === '') return t('card_item.not_available')
        const rawValue = String(value)
        return formatDateTime(rawValue) || rawValue
    }

    const collectedDisplay = computed(() => formatMetadataDate(props.collected))
    const publishedDisplay = computed(() => formatMetadataDate(props.published))
    const supersededDisplay = computed(() => formatMetadataDate(props.superseded))
    const sourceDisplay = computed(() => props.source || t('card_item.not_available'))
    const authorDisplay = computed(() => props.author || t('card_item.not_available'))
    const sanitizedContent = computed(() => sanitizeNewsItemHtml(props.content))

    const isSafeLink = computed(() => {
        try {
            return ['http:', 'https:'].includes(new URL(props.link || '').protocol)
        } catch {
            return false
        }
    })
</script>

<style scoped>
    /* Pinned metadata header + footer link, scrolling body. The dialog stretches this pane
       to its grid cell, so .source-body can scroll. */
    .source-tab {
        display: flex;
        flex-direction: column;
    }

    .source-header {
        flex: 0 0 auto;
        padding: 24px 24px 0;
    }

    /* flex-basis: auto (not 0) so a long article counts toward the dialog height, letting
       it grow to the 90vh cap; min-height: 0 lets it then shrink and scroll internally. */
    .source-body {
        flex: 1 1 auto;
        min-height: 0;
        overflow-y: auto;
        padding: 8px 24px;
    }

    .source-footer {
        flex: 0 0 auto;
        padding: 0 24px 24px;
    }

    /* Collected content is injected by v-html, so it carries no scope attribute - :deep()
       is the only way to reach it. Preformatted bodies (a plain text email, an article the
       RSS collector could not parse as HTML) keep their line breaks and indentation, but
       must wrap: unwrapped <pre> would scroll the whole dialog sideways. */
    .source-body :deep(pre) {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        margin: 0;
        /* Monospace (the <pre> default) is kept on purpose: it is what holds the columns of
           an ASCII table or a signature block together. */
        font-size: inherit;
    }

    /* Nothing in an article may push the dialog wider than the pane. */
    .source-body :deep(*) {
        max-width: 100%;
    }
</style>
