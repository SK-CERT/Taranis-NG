<script setup lang="ts">
    withDefaults(defineProps<{ compact?: boolean; variant?: 'assess' | 'report' | 'product' | 'asset'; hideActions?: boolean }>(), {
        compact: false,
        variant: 'assess',
        hideActions: false
    })
</script>

<template>
    <div class="content-skeleton">
        <v-skeleton-loader
            v-for="index in 3"
            :key="index"
            class="content-skeleton__card"
            :class="{
                'content-skeleton__card--structured': variant !== 'assess' && !compact,
                'content-skeleton__card--product': variant === 'product' && !compact,
                'content-skeleton__card--asset': variant === 'asset' && !compact
            }"
            :type="
                compact
                    ? 'heading, text'
                    : variant === 'asset'
                      ? 'asset'
                      : variant !== 'assess'
                        ? 'report'
                        : 'metadata, heading, paragraph, footer'
            "
            :types="{
                'asset': hideActions ? 'avatar, identity, description, chip' : 'avatar, identity, description, chip, actions',
                'identity': 'heading, text',
                'description': 'text',
                'metadata': 'text@3',
                'footer': 'text, actions',
                'actions': variant === 'product' || variant === 'asset' ? 'button' : variant === 'report' ? 'button@2' : 'button@7',
                'report': hideActions ? 'avatar, report-content' : 'avatar, report-content, actions',
                'report-content': 'report-meta, heading, report-details',
                'report-meta': 'text@2',
                'report-details': variant === 'product' ? 'chip, text, text' : 'chip, text'
            }"
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
    .content-skeleton__card--structured :deep(.v-skeleton-loader__report) {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        gap: 0.65rem;
        padding: 12px;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__avatar) {
        flex: none;
        width: 38px;
        min-width: 38px;
        max-width: 38px;
        height: 38px;
        min-height: 38px;
        max-height: 38px;
        border-radius: 4px;
        margin: 0;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__report-content) {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        min-width: 0;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__report-meta) {
        justify-content: space-between;
        flex-wrap: nowrap;
        gap: 16px;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__report-meta > .v-skeleton-loader__text) {
        flex: 0 1 90px;
        height: 10px;
        margin: 0;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__report-meta > .v-skeleton-loader__text:last-child) {
        flex-basis: 260px;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__heading) {
        flex: none;
        width: 45%;
        height: 18px;
        margin: 0;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__report-details) {
        flex-wrap: nowrap;
        gap: 10px;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__chip) {
        flex: 0 1 130px;
        max-width: 130px;
        height: 22px;
        margin: 0;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__report-details > .v-skeleton-loader__text) {
        flex: 0 0 30px;
        height: 10px;
        margin: 0;
    }

    .content-skeleton__card--structured :deep(.v-skeleton-loader__actions) {
        flex-wrap: nowrap;
        padding-inline-start: 16px;
        border-inline-start: 1px solid rgba(var(--v-theme-outline), 0.24);
    }

    .content-skeleton__card--product :deep(.v-skeleton-loader__report-details > .v-skeleton-loader__text:last-child) {
        flex: 0 1 100px;
    }

    .content-skeleton__card--asset :deep(.v-skeleton-loader__asset) {
        display: grid;
        grid-template-columns: auto minmax(11rem, 0.55fr) minmax(14rem, 1fr) auto auto;
        align-items: center;
        gap: 0.7rem;
        min-height: 68px;
        padding: 0.5rem 0.65rem;
    }

    .content-skeleton__card--asset :deep(.v-skeleton-loader__identity) {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        min-width: 0;
    }

    .content-skeleton__card--asset :deep(.v-skeleton-loader__identity > .v-skeleton-loader__heading) {
        width: 60%;
        max-width: 180px;
        height: 16px;
        margin: 0;
    }

    .content-skeleton__card--asset :deep(.v-skeleton-loader__text) {
        flex: none;
        width: 75%;
        max-width: 240px;
        height: 10px;
        margin: 0;
    }

    .content-skeleton__card--asset :deep(.v-skeleton-loader__chip) {
        width: 130px;
        height: 24px;
        max-width: 130px;
        margin: 0;
        border-radius: 3px;
    }

    @media (max-width: 650px) {
        .content-skeleton__card--asset :deep(.v-skeleton-loader__asset) {
            grid-template-columns: auto minmax(0, 1fr) auto auto;
            gap: 0.5rem;
        }

        .content-skeleton__card--asset :deep(.v-skeleton-loader__description) {
            display: none;
        }
    }

    @media (max-width: 720px) {
        .content-skeleton__card--structured :deep(.v-skeleton-loader__report) {
            grid-template-columns: auto minmax(0, 1fr);
        }

        .content-skeleton__card--structured :deep(.v-skeleton-loader__report > .v-skeleton-loader__actions) {
            grid-column: 2;
            border-inline-start: 0;
            padding-inline-start: 0;
        }
    }
</style>
