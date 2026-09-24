<template>
    <v-container
        fluid
        class="pa-0"
    >
        <ToolbarFilter
            :total-count="store.externalUsers.total_count"
            total-count-title="external_user.total_count"
            @update-filter="setFilter"
        >
            <template #addbutton><AddNewButton @click="openCreate" /></template>
        </ToolbarFilter>
        <ContentData
            :items="store.externalUsers.items"
            card-item="CardCompact"
            delete-permission="MY_ASSETS_CONFIG"
            :loading="loading"
            @edit="openEdit"
            @delete="remove"
            @refresh="load"
        />
        <NewExternalUser
            v-model="dialog"
            :user="selected"
            @saved="load"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { onMounted, ref } from 'vue'
    import { useConfigStore } from '@/stores/config'
    import { deleteExternalUser } from '@/api/config'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import NewExternalUser from '@/components/config/external/NewExternalUser.vue'

    type User = { id?: number; username: string; name: string; permissions?: Array<{ id: number }> }
    const store = useConfigStore()
    const loading = ref(false)
    const filter = ref({ search: '' })
    const dialog = ref(false)
    const selected = ref<User | null>(null)
    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }
    const load = async (): Promise<void> => {
        loading.value = true
        try {
            await store.loadExternalUsers(filter.value)
        } catch {
            notify('error', 'external_user.load_error')
        } finally {
            loading.value = false
        }
    }
    const setFilter = (value: { search: string }): void => {
        filter.value = value
        load()
    }
    const openCreate = (): void => {
        selected.value = null
        dialog.value = true
    }
    const openEdit = (value: unknown): void => {
        selected.value = value as User
        dialog.value = true
    }
    const remove = async (value: unknown): Promise<void> => {
        try {
            await deleteExternalUser(value)
            notify('success', 'external_user.removed')
            await load()
        } catch {
            notify('error', 'external_user.removed_error')
        }
    }
    onMounted(load)
</script>
