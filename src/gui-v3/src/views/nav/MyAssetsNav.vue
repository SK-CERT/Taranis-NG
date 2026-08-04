<template>
    <div
        v-if="loading"
        class="pa-4 text-center"
    >
        <v-progress-circular
            indeterminate
            color="primary"
        />
    </div>
    <v-alert
        v-else-if="loadError"
        class="ma-2"
        type="error"
        variant="tonal"
    >
        {{ $t('error.load_groups') }}
        <template #append>
            <v-btn
                :disabled="loading"
                size="small"
                variant="text"
                @click="loadGroups"
            >
                {{ $t('settings.reload') }}
            </v-btn>
        </template>
    </v-alert>
    <v-alert
        v-else-if="links.length === 0"
        class="ma-2"
        type="info"
        variant="tonal"
    >
        {{ $t('asset.no_groups_message') }}
    </v-alert>
    <GroupNavList
        v-else
        :groups="links"
        :active-id="activeGroupId"
        title-key="asset.groups"
        @select="selectGroup"
    />
</template>

<script setup lang="ts">
    import { computed, onMounted, ref, watch } from 'vue'
    import { useRoute, useRouter } from 'vue-router'
    import GroupNavList from '@/components/common/GroupNavList.vue'
    import { useAssetsStore } from '@/stores/assets'

    const store = useAssetsStore()
    const route = useRoute()
    const router = useRouter()
    const loading = ref(false)
    const loadError = ref(false)
    const groupsLoaded = ref(false)
    let loadPromise: Promise<void> | null = null
    const activeGroupId = computed(() => String(route.params['groupId'] || ''))
    const links = computed(() =>
        store.assetGroups.items.map((group) => ({
            id: group.id,
            icon: 'mdi-folder-multiple',
            title: group.name,
            route: `/myassets/group/${group.id}`
        }))
    )
    const selectGroup = async (group: { route?: string }): Promise<void> => {
        if (group.route && group.route !== route.path) await router.push(group.route)
    }

    const reconcileRoute = async (): Promise<void> => {
        if (!groupsLoaded.value || loadError.value) return

        const firstGroup = links.value[0]
        if (!firstGroup) {
            if (route.path !== '/myassets') await router.replace('/myassets')
            return
        }

        const hasActiveGroup = links.value.some((group) => String(group.id) === activeGroupId.value)
        if (!hasActiveGroup) await router.replace(firstGroup.route)
    }

    const loadGroups = (): Promise<void> => {
        if (loadPromise) return loadPromise

        loadPromise = (async () => {
            loading.value = true
            loadError.value = false
            groupsLoaded.value = false
            try {
                await store.loadAssetGroups({ search: '' })
                groupsLoaded.value = true
            } catch {
                loadError.value = true
            } finally {
                loading.value = false
                loadPromise = null
            }

            await reconcileRoute()
        })()

        return loadPromise
    }

    watch(activeGroupId, () => void reconcileRoute())
    onMounted(() => void loadGroups())
</script>
