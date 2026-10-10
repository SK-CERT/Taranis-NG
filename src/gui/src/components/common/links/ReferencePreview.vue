<template>
    <div
        v-if="cited.length > 0"
        class="reference-preview d-flex flex-wrap ga-1 pt-1"
        role="list"
        :aria-label="t('links.citations')"
        data-test="reference-preview"
    >
        <template
            v-for="entry in cited"
            :key="entry.key"
        >
            <v-chip
                v-if="entry.link"
                role="listitem"
                size="x-small"
                variant="tonal"
                :href="isHttpUrl(entry.link.url) ? entry.link.url : undefined"
                target="_blank"
                rel="noopener noreferrer"
                :title="entry.link.url"
                data-test="reference-chip"
            >
                <span class="reference-preview__number">[{{ entry.link.number }}]</span>
                <bdi dir="ltr">{{ shortUrl(entry.link.url) }}</bdi>
            </v-chip>
            <v-chip
                v-else
                role="listitem"
                size="x-small"
                variant="tonal"
                color="warning"
                :prepend-icon="ICONS.LINK_OFF"
                :title="t('links.missing_hint')"
                data-test="reference-missing"
            >
                {{ t('links.missing') }}
            </v-chip>
        </template>
    </div>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import { citedKeys, isHttpUrl, shortUrl, type CitableLink } from '@/utils/linkReferences'

    /** Shows what each citation in a text resolves to, and flags citations of removed links. */
    const props = defineProps<{
        text: unknown
        resolve: (key: string) => CitableLink | undefined
    }>()

    const { t } = useI18n()

    // Each cited link once, in order of first citation.
    const cited = computed(() =>
        [...new Set(citedKeys(props.text))].map((key) => ({
            key,
            link: props.resolve(key)
        }))
    )
</script>

<style scoped>
    .reference-preview__number {
        margin-inline-end: 4px;
        font-weight: 600;
    }
</style>
