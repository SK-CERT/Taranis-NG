<template>
    <v-list density="compact">
        <!-- Group links -->
        <v-list-subheader>{{ $t('analyze.source') }}</v-list-subheader>
        <v-list-item v-for="link in links" :key="link.route" :to="link.route" class="pa-2">
            <template #default>
                <div class="d-flex flex-column align-center text-center">
                    <v-icon :color="link.color || undefined" class="mb-2">
                        {{ link.icon }}
                    </v-icon>
                    <span class="text-body-small">
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

    type AnalyzeNavLink = {
        icon: string
        title: string
        translate: boolean
        route: string
        color?: string
    }

    const router = useRouter()
    const route = useRoute()
    const { global: themeGlobal } = useTheme()
    const analyzeStore = useAnalyzeStore()

    const groups = ref<Array<string | number>>([])
    const links = ref<AnalyzeNavLink[]>([])

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
                const groupTitle = String(group)
                links.value.push({
                    icon: 'mdi-arrow-down-bold-circle-outline',
                    title: groupTitle,
                    translate: false,
                    route: '/analyze/group-' + groupTitle.replaceAll(' ', '-')
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
