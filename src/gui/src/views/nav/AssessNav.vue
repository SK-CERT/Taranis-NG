<template>
    <NavSkeleton v-if="loading" />
    <GroupNavList
        v-else
        :groups="groups"
        :active-id="activeGroupId"
        :unread-counts="unreadCounts"
        @select="onSelect"
    />
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted } from 'vue'
    import { useRouter, useRoute } from 'vue-router'
    import { useConfigStore } from '@/stores/config'
    import { getUnreadCountsByGroup } from '@/api/assess'
    import GroupNavList from '@/components/common/GroupNavList.vue'
    import NavSkeleton from '@/components/common/NavSkeleton.vue'
    import { type GroupNavItem } from '@/types/routing'

    const router = useRouter()
    const route = useRoute()
    const configStore = useConfigStore()

    const loading = ref(true)
    const groups = ref<GroupNavItem[]>([])
    const unreadCounts = ref<Record<string, number> | null>(null)

    // Highlight the group matching the current /assess/group/:groupId route.
    const activeGroupId = computed<string | null>(() => (route.params['groupId'] as string) ?? null)

    const onSelect = (group: { route?: string }): void => {
        if (group.route) router.push(group.route)
    }

    // Responses can overtake each other; only the latest request may set the counts.
    let unreadRequest = 0

    const loadUnreadCounts = async (): Promise<void> => {
        const request = ++unreadRequest
        try {
            const response = await getUnreadCountsByGroup()
            if (request === unreadRequest) {
                unreadCounts.value = response.data
            }
        } catch (error) {
            console.error('Error loading unread news item counts:', error)
        }
    }

    // The server announces every change to the news items - a collector run, an item read or
    // deleted by anyone - and a collector run announces each batch. Coalesce those into one
    // reload: a throttle rather than a debounce, so a steady stream still updates the counts.
    const UNREAD_REFRESH_COALESCE_MS = 500
    let unreadRefreshTimer: ReturnType<typeof setTimeout> | undefined

    const handleNewsItemsUpdated = (): void => {
        if (unreadRefreshTimer) {
            return
        }
        unreadRefreshTimer = setTimeout(() => {
            unreadRefreshTimer = undefined
            void loadUnreadCounts()
        }, UNREAD_REFRESH_COALESCE_MS)
    }

    onMounted(async () => {
        window.addEventListener('news-items-updated', handleNewsItemsUpdated)
        void loadUnreadCounts()
        try {
            await configStore.loadOSINTSourceGroupsAssess({ search: '' })
            groups.value = configStore.osintSourceGroupsForAssess as GroupNavItem[]
        } catch (error) {
            console.error('Error loading OSINT source groups:', error)
        } finally {
            loading.value = false
        }
    })

    onUnmounted(() => {
        clearTimeout(unreadRefreshTimer)
        window.removeEventListener('news-items-updated', handleNewsItemsUpdated)
    })
</script>
