<template>
    <v-list
        density="compact"
        class="section-navigation"
    >
        <!-- Group links -->
        <v-list-subheader>{{ $t('analyze.source') }}</v-list-subheader>
        <v-list-item
            v-for="link in links"
            :key="link.route"
            :to="link.route"
            class="section-navigation__item"
        >
            <template #default>
                <div class="section-navigation__content">
                    <v-icon
                        :color="link.color || undefined"
                        size="22"
                    >
                        {{ link.icon }}
                    </v-icon>
                    <span class="section-navigation__label">
                        {{ link.translate ? $t(link.title) : link.title }}
                    </span>
                </div>
            </template>
        </v-list-item>
    </v-list>
</template>

<script setup lang="ts">
    import { ref, onMounted, computed } from 'vue'
    import { useRouter, useRoute } from 'vue-router'
    import { useTheme } from 'vuetify'
    import { useAnalyzeStore } from '@/stores/analyze'
    import { type GroupNavItem } from '@/types/routing'

    const router = useRouter()
    const route = useRoute()
    const { global: themeGlobal } = useTheme()
    const analyzeStore = useAnalyzeStore()

    const groups = ref<Array<string | number>>([])
    const links = ref<GroupNavItem[]>([])

    const isDark = computed(() => themeGlobal.name.value === 'dark')
    const textColor = computed(() => (isDark.value ? '#ffffff' : '#000000'))
    const iconColor = computed(() => (isDark.value ? '#ffffff' : 'rgba(0, 0, 0, 0.54)'))
    const dividerColor = computed(() => (isDark.value ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.12)'))

    onMounted(async () => {
        try {
            await analyzeStore.loadReportItemGroups({})
            const reportGroups = analyzeStore.getReportItemGroups
            groups.value = Array.isArray(reportGroups) ? (reportGroups as Array<string | number>) : []

            // Add local link
            links.value.push({
                id: 'local',
                icon: 'mdi-home-circle-outline',
                title: 'nav_menu.local',
                translate: true,
                route: '/analyze/local'
            })

            // Add group links (groups are just strings)
            const groupArray = Array.isArray(groups.value) ? groups.value : []
            for (let i = 0; i < groupArray.length; i++) {
                const group = groupArray[i]
                if (group === undefined || group === null) {
                    continue
                }
                const groupId = String(group).replaceAll(' ', '-')
                links.value.push({
                    id: groupId,
                    icon: 'mdi-arrow-down-bold-circle-outline',
                    title: String(group),
                    translate: false,
                    route: '/analyze/group-' + groupId
                })
            }

            // If not on a specific scope route, redirect to local
            if (!route.params['scope']) {
                router.push('/analyze/local')
            }
        } catch (error) {
            console.error('Error loading report item groups:', error)
        }
    })
</script>

<style scoped>
    .section-navigation__item {
        padding: 0.35rem 0.45rem !important;
    }

    .section-navigation__content {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 0;
    }

    .section-navigation__label {
        overflow: hidden;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1.2;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
</style>
