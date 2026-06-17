<template>
    <v-list density="compact">
        <!-- Config links with permission filtering -->
        <v-list-item v-for="link in filteredLinks" :key="link.id" :to="link.route" style="padding: 8px 8px; min-height: auto">
            <template #default>
                <v-divider v-if="link.separator" />
                <div v-else style="display: flex; flex-direction: column; align-items: center">
                    <v-icon :color="link.color || undefined" style="margin-bottom: 6px">
                        {{ link.icon }}
                    </v-icon>
                    <span style="font-size: 0.8rem; line-height: 1.4; text-align: center">
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
