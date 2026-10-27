<template>
    <span
        v-if="state && (state.origin === 'ai' || state.outdated)"
        class="d-inline-flex align-center ga-1"
    >
        <v-chip
            v-if="state.origin === 'ai'"
            size="x-small"
            color="info"
            variant="tonal"
            :title="t('report_item.translation.ai_hint')"
            data-test="translation-ai"
        >
            {{ t('report_item.translation.ai') }}
        </v-chip>
        <v-chip
            v-if="state.outdated"
            size="x-small"
            color="warning"
            variant="tonal"
            :title="t('report_item.translation.outdated_hint')"
            data-test="translation-outdated"
        >
            {{ t('report_item.translation.outdated') }}
        </v-chip>
        <!-- Reviewing an AI translation also checks it against the current source. -->
        <v-btn
            v-if="state.origin === 'ai' && reviewable"
            icon="mdi-check"
            variant="text"
            density="compact"
            size="small"
            color="success"
            tabindex="-1"
            :title="t('report_item.translation.review')"
            data-test="translation-review"
            @mousedown.stop
            @click.stop="emit('review')"
        />
    </span>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'

    /**
     * How a translation came about: written by the AI (until somebody edits or reviews it), and
     * whether its source changed since. With `reviewable`, the AI chip offers to mark it reviewed.
     */
    export type TranslationStateValue = {
        value: string
        origin: 'ai' | 'manual'
        version: number
        outdated: boolean
        user?: string | null
        last_updated?: string | null
    }

    defineProps<{
        state?: TranslationStateValue | null | undefined
        reviewable?: boolean
    }>()

    const emit = defineEmits<{ (e: 'review'): void }>()

    const { t } = useI18n()
</script>
