<template>
    <v-list density="compact">
        <!-- Config links with permission filtering -->
        <v-list-item v-for="link in filteredLinks" :key="link.id" :to="link.route" class="pa-2" style="min-height: auto">
            <template #default>
                <v-divider v-if="link.separator" />
                <div v-else class="d-flex flex-column align-center text-center">
                    <v-icon :color="link.color || undefined" class="mb-2">
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
    import { useTheme } from 'vuetify'
    import { useAuth } from '@/composables/useAuth'
    import { filterConfigLinks } from '@/config/config-nav-links'

    const { checkPermission } = useAuth()
    const { global: themeGlobal } = useTheme()
    const isDark = computed(() => themeGlobal.name.value === 'dark')

    // Filter links based on permissions and remove leading/trailing separators
    const filteredLinks = computed(() => filterConfigLinks(checkPermission))
</script>
