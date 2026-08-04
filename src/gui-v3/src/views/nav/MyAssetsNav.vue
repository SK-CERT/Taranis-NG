<template>
    <GroupNavList
        :groups="links"
        :active-id="activeGroupId"
        title-key="asset.groups"
        @select="selectGroup"
    />
</template>

<script setup lang="ts">
    import { computed, onMounted } from 'vue'
    import { useRoute, useRouter } from 'vue-router'
    import GroupNavList from '@/components/common/GroupNavList.vue'
    import { useAssetsStore } from '@/stores/assets'

    const store = useAssetsStore()
    const route = useRoute()
    const router = useRouter()
    const activeGroupId = computed(() => String(route.params['groupId'] || ''))
    const links = computed(() =>
        store.assetGroups.items.map((group) => ({
            id: group.id,
            icon: 'mdi-folder-multiple',
            title: group.name,
            route: `/myassets/group/${group.id}`
        }))
    )
    const selectGroup = (group: { route?: string }): void => {
        if (group.route) router.push(group.route)
    }

    onMounted(async () => {
        await store.loadAssetGroups({ search: '' })
        if (!route.params['groupId'] && links.value[0]) await router.replace(links.value[0].route)
    })
</script>
