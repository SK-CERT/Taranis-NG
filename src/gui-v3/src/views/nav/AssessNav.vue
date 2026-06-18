<template>
    <GroupNavList :groups="groups" :active-id="activeGroupId" @select="onSelect" />
</template>

<script setup lang="ts">
    import { ref, computed, onMounted } from 'vue'
    import { useRouter, useRoute } from 'vue-router'
    import { useConfigStore } from '@/stores/config'
    import GroupNavList from '@/components/common/GroupNavList.vue'

    type AssessGroup = {
        id: string | number
        icon: string
        color: string | null
        title: string
        translate: string
        route: string
    }

    const router = useRouter()
    const route = useRoute()
    const configStore = useConfigStore()

    const groups = ref<AssessGroup[]>([])

    // Highlight the group matching the current /assess/group/:groupId route.
    const activeGroupId = computed<string | null>(() => (route.params['groupId'] as string) ?? null)

    const onSelect = (group: { route?: string }): void => {
        if (group.route) router.push(group.route)
    }

    onMounted(async () => {
        try {
            await configStore.loadOSINTSourceGroupsAssess({ search: '' })
            groups.value = configStore.osintSourceGroupsForAssess as AssessGroup[]

            // If not on a specific group route and groups exist, redirect to first
            if (!route.path.includes('/group/') && groups.value.length > 0) {
                const firstGroup = groups.value[0]
                if (firstGroup) {
                    router.push(firstGroup.route)
                }
            }
        } catch (error) {
            console.error('Error loading OSINT source groups:', error)
        }
    })
</script>
