<script setup lang="ts">
    withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
</script>

<template>
    <div class="content-skeleton">
        <v-skeleton-loader
            v-for="index in 3"
            :key="index"
            class="content-skeleton__card"
            :type="compact ? 'heading, text' : 'metadata, heading, paragraph, footer'"
            :types="{ metadata: 'text@3', footer: 'text, actions', actions: 'button@7' }"
        />
    </div>
</template>

<style scoped>
    .content-skeleton__card {
        background: var(--review-list-row);
        border-bottom: 1px solid var(--review-panel-border);
        border-radius: 0;
    }

    .content-skeleton__card :deep(.v-skeleton-loader__heading) {
        flex-basis: 65%;
        max-width: 65%;
        height: 18px;
    }

    .content-skeleton__card :deep(.v-skeleton-loader__metadata) {
        justify-content: space-between;
        flex-wrap: nowrap;
        padding: 12px 16px 0;
    }

    .content-skeleton__card :deep(.v-skeleton-loader__metadata > .v-skeleton-loader__text) {
        flex: 0 1 18%;
        height: 10px;
        margin: 0;
    }

    .content-skeleton__card :deep(.v-skeleton-loader__paragraph > .v-skeleton-loader__text) {
        height: 10px;
    }

    .content-skeleton__card :deep(.v-skeleton-loader__footer) {
        justify-content: space-between;
        gap: 16px;
        padding: 8px 16px 16px;
    }

    .content-skeleton__card :deep(.v-skeleton-loader__footer > .v-skeleton-loader__text) {
        flex: 0 1 35%;
        height: 10px;
        margin: 0;
    }

    .content-skeleton__card :deep(.v-skeleton-loader__actions) {
        flex: 0 1 auto;
        gap: 12px;
    }

    .content-skeleton__card :deep(.v-skeleton-loader__button) {
        flex: 0 0 18px;
        width: 18px;
        height: 18px;
        margin: 0;
    }
</style>
