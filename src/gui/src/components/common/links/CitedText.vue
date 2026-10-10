<template>
    <span class="cited-text"
        ><template
            v-for="(segment, index) in segments"
            :key="index"
            ><template v-if="'text' in segment">{{ segment.text }}</template
            ><a
                v-else-if="segment.link && isHttpUrl(segment.link.url)"
                class="cited-text__citation"
                :href="segment.link.url"
                :title="segment.link.url"
                target="_blank"
                rel="noopener noreferrer"
                >[{{ segment.link.number }}]</a
            ><span
                v-else-if="segment.link"
                class="cited-text__citation"
                :title="segment.link.url"
                >[{{ segment.link.number }}]</span
            ><span
                v-else
                class="cited-text__citation cited-text__citation--missing"
                :title="t('links.missing_hint')"
                >[?]</span
            ></template
        ></span
    >
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { isHttpUrl, splitReferences, type CitableLink } from '@/utils/linkReferences'

    /** Plain text with its link citations shown as the numbers of the cited links. */
    const props = defineProps<{
        text: unknown
        resolve: (key: string) => CitableLink | undefined
    }>()

    const { t } = useI18n()

    const segments = computed(() => splitReferences(props.text, props.resolve))
</script>

<style scoped>
    .cited-text__citation {
        color: rgb(var(--v-theme-primary));
        font-weight: 600;
        text-decoration: none;
    }

    .cited-text__citation--missing {
        color: rgb(var(--v-theme-warning));
    }
</style>
