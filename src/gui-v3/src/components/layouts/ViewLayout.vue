<template>
    <div
        class="view"
        :class="{ 'view--integrated-toolbar': integratedToolbar }"
    >
        <div class="view-panel">
            <slot name="panel" />
        </div>
        <div class="view-content">
            <slot name="content" />
        </div>
    </div>
</template>

<script setup lang="ts">
    withDefaults(
        defineProps<{
            integratedToolbar?: boolean
        }>(),
        {
            integratedToolbar: false
        }
    )
</script>

<style scoped>
    .view {
        display: flex;
        flex-direction: column;
        height: 100%;
        width: 100%;
        min-width: 0;
        padding: clamp(0.4rem, 0.8vw, 0.75rem);
        gap: 0.7rem;
        background: var(--review-workspace);
    }

    .view-panel {
        flex: 0 0 auto;
        position: sticky;
        top: 0.4rem;
        z-index: 10;
        background: rgb(var(--v-theme-surface));
        overflow: hidden;
        border: 2px solid var(--review-panel-border);
        border-radius: 5px;
        box-shadow: 0 2px 8px rgba(18, 44, 70, 0.08);
    }

    .view-content {
        flex: 1 1 auto;
        overflow-y: auto;
        overflow-x: hidden;
        min-height: 0;
        background: var(--review-list-row);
        border: 2px solid var(--review-panel-border);
        border-radius: 4px;
    }

    .view--integrated-toolbar {
        gap: 0;
    }

    .view--integrated-toolbar .view-panel {
        border: 2px solid rgb(var(--v-theme-surface));
        border-inline-width: 5px;
        border-radius: 4px 4px 0 0;
        box-shadow: 0 3px 10px rgba(18, 44, 70, 0.16);
    }

    @media (max-width: 700px) {
        .view {
            padding: 0.35rem;
            gap: 0.35rem;
        }

        .view-panel {
            top: 0.35rem;
            border-radius: 4px;
        }
    }
</style>
