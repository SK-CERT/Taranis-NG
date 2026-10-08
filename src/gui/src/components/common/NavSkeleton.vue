<template>
    <v-skeleton-loader
        class="nav-skeleton"
        color="drawer-bg"
        type="text, list-item-avatar@5"
    />
</template>

<style scoped>
    .nav-skeleton {
        padding-block: 8px;
    }

    .nav-skeleton > :deep(.v-skeleton-loader__text) {
        flex: 0 0 64px;
        height: 10px;
        margin: 15px 16px;
    }

    .nav-skeleton :deep(.v-skeleton-loader__list-item-avatar) {
        flex: 0 0 100%;
        flex-wrap: nowrap;
        gap: 8px;
        height: 40px;
        padding: 0.35rem 0.45rem;
    }

    .nav-skeleton :deep(.v-skeleton-loader__avatar) {
        flex: 0 0 22px;
        width: 22px;
        height: 22px;
        min-width: 22px;
        max-width: 22px;
        min-height: 22px;
        max-height: 22px;
        border-radius: 4px;
        margin: 0;
    }

    .nav-skeleton :deep(.v-skeleton-loader__avatar + .v-skeleton-loader__text) {
        flex: 1 1 0;
        height: 12px;
        max-width: 90px;
        margin: 0;
    }
</style>
