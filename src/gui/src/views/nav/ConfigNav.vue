<template>
    <v-list
        density="compact"
        class="ms-1"
    >
        <!-- Config links with permission filtering -->
        <v-list-item
            v-for="link in filteredLinks"
            :key="link.id"
            :to="link.route"
            class="pa-2"
            style="min-height: auto"
        >
            <template #default>
                <v-divider v-if="link.separator" />
                <div
                    v-else
                    class="d-flex flex-column align-center text-center"
                >
                    <v-icon
                        :color="link.color || undefined"
                        class="mb-2"
                    >
                        {{ link.icon }}
                    </v-icon>
                    <span class="text-body-small">
                        {{ link.translate ? $t(link.title ?? '') : link.title }}
                    </span>
                </div>
            </template>
        </v-list-item>
    </v-list>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useAuth } from '@/composables/useAuth'
    import { filterConfigLinks } from '@/config/config-nav-links'

    const { checkPermission } = useAuth()

    // Filter links based on permissions and remove leading/trailing separators
    const filteredLinks = computed(() => filterConfigLinks(checkPermission))
</script>

<style scoped>
    .v-list-item--active {
        background-color: rgba(var(--v-theme-primary), 0.16);
        box-shadow: inset 3px 0 rgb(var(--v-theme-primary));
        color: rgb(var(--v-theme-primary));
    }

    .v-list-item--active .v-icon {
        color: rgb(var(--v-theme-primary));
    }

    /* Keep the active highlight grey (the overlay otherwise inherits the primary
       text colour via currentColor and turns blue). The overlay is rendered inside
       Vuetify's VListItem, so :deep() is required to reach it from a scoped block. */
    .v-list-item--active > :deep(.v-list-item__overlay) {
        background-color: rgb(var(--v-theme-on-surface));
    }
</style>
