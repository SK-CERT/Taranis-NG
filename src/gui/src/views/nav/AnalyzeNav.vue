<template>
    <NavSkeleton v-if="loading" />
    <GroupNavList
        v-else
        :groups="links"
        :active-id="activeGroupId"
        title-key="analyze.source"
        @select="onSelect"
    />
</template>

<script setup lang="ts">
    import { computed, ref, onMounted } from 'vue'
    import { useRouter, useRoute } from 'vue-router'
    import { useAnalyzeStore } from '@/stores/analyze'
    import GroupNavList from '@/components/common/GroupNavList.vue'
    import NavSkeleton from '@/components/common/NavSkeleton.vue'
    import { type GroupNavItem } from '@/types/routing'
    import { createRemoteAnalyzePath } from '@/utils/analyze-routing'

    const router = useRouter()
    const route = useRoute()
    const analyzeStore = useAnalyzeStore()

    const loading = ref(true)
    const groups = ref<Array<string | number>>([])
    const links = ref<GroupNavItem[]>([])
    // Highlight the group matching the current /assess/group/:groupId route.
    const activeGroupId = computed(() => {
        const REMOTE_SCOPE_PREFIX = 'group-'
        const scope = String(route.params['scope'] || '')
        return scope.startsWith(REMOTE_SCOPE_PREFIX) ? scope.substring(REMOTE_SCOPE_PREFIX.length) : scope
    })

    const onSelect = (group: { route?: string }): void => {
        if (group.route) router.push(group.route)
    }

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
                const groupName = String(group)
                links.value.push({
                    id: groupName,
                    icon: 'mdi-arrow-down-bold-circle-outline',
                    title: groupName,
                    translate: false,
                    route: createRemoteAnalyzePath(groupName)
                })
            }

            // If not on a specific scope route, redirect to local
            if (!route.params['scope']) {
                router.push('/analyze/local')
            }
        } catch (error) {
            console.error('Error loading report item groups:', error)
        } finally {
            loading.value = false
        }
    })
</script>
